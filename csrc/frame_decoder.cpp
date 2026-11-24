// Fast video frame decoder exposed to Python via pybind11.
//
// Uses FFmpeg's libavformat/libavcodec directly with frame+slice threading and
// converts each decoded frame to packed RGB24 with libswscale, writing straight
// into a NumPy buffer. The GIL is released while decoding so Python threads
// (e.g. the detector) can make progress.

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <stdexcept>
#include <string>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}

namespace py = pybind11;

namespace {

std::string av_err(int code) {
    char buf[AV_ERROR_MAX_STRING_SIZE] = {0};
    av_strerror(code, buf, sizeof(buf));
    return std::string(buf);
}

class FrameDecoder {
public:
    FrameDecoder(const std::string& path, int threads) {
        int rc = avformat_open_input(&fmt_, path.c_str(), nullptr, nullptr);
        if (rc < 0) throw std::runtime_error("cannot open " + path + ": " + av_err(rc));
        if ((rc = avformat_find_stream_info(fmt_, nullptr)) < 0)
            throw std::runtime_error("no stream info: " + av_err(rc));

        const AVCodec* codec = nullptr;
        stream_ = av_find_best_stream(fmt_, AVMEDIA_TYPE_VIDEO, -1, -1, &codec, 0);
        if (stream_ < 0 || !codec) throw std::runtime_error("no video stream in " + path);
        AVStream* st = fmt_->streams[stream_];

        ctx_ = avcodec_alloc_context3(codec);
        avcodec_parameters_to_context(ctx_, st->codecpar);
        ctx_->thread_count = threads;  // 0 = let FFmpeg pick (one per core)
        ctx_->thread_type = FF_THREAD_FRAME | FF_THREAD_SLICE;
        if ((rc = avcodec_open2(ctx_, codec, nullptr)) < 0)
            throw std::runtime_error("cannot open codec: " + av_err(rc));

        width_ = ctx_->width;
        height_ = ctx_->height;
        AVRational r = st->avg_frame_rate.num ? st->avg_frame_rate : st->r_frame_rate;
        fps_ = r.den ? av_q2d(r) : 0.0;
        frame_count_ = st->nb_frames;

        pkt_ = av_packet_alloc();
        frame_ = av_frame_alloc();
    }

    ~FrameDecoder() {
        sws_freeContext(sws_);
        av_frame_free(&frame_);
        av_packet_free(&pkt_);
        avcodec_free_context(&ctx_);
        avformat_close_input(&fmt_);
    }

    FrameDecoder(const FrameDecoder&) = delete;
    FrameDecoder& operator=(const FrameDecoder&) = delete;

    // Returns the next frame as an (H, W, 3) uint8 RGB array, or None at EOF.
    py::object read() {
        if (eof_) return py::none();
        py::array_t<uint8_t> out({height_, width_, 3});
        uint8_t* dst = out.mutable_data();
        bool ok;
        {
            py::gil_scoped_release release;
            ok = decode_into(dst);
        }
        if (!ok) {
            eof_ = true;
            return py::none();
        }
        ++index_;
        return std::move(out);
    }

    // Decodes the next frame into a caller-owned (H, W, 3) uint8 buffer; returns false at EOF.
    bool read_into(py::array_t<uint8_t, py::array::c_style> buf) {
        if (buf.ndim() != 3 || buf.shape(0) != height_ || buf.shape(1) != width_ || buf.shape(2) != 3)
            throw std::invalid_argument("buffer must have shape (height, width, 3)");
        if (eof_) return false;
        uint8_t* dst = buf.mutable_data();
        bool ok;
        {
            py::gil_scoped_release release;
            ok = decode_into(dst);
        }
        if (!ok) {
            eof_ = true;
            return false;
        }
        ++index_;
        return true;
    }

    int width() const { return width_; }
    int height() const { return height_; }
    double fps() const { return fps_; }
    int64_t frame_count() const { return frame_count_; }
    int64_t index() const { return index_; }

private:
    // Pull the next decoded frame and convert it to RGB in `dst`.
    bool decode_into(uint8_t* dst) {
        while (true) {
            int rc = avcodec_receive_frame(ctx_, frame_);
            if (rc == 0) {
                convert(dst);
                av_frame_unref(frame_);
                return true;
            }
            if (rc == AVERROR_EOF) return false;
            if (rc != AVERROR(EAGAIN)) throw std::runtime_error("decode error: " + av_err(rc));

            // Decoder needs input: feed the next video packet, or flush at end of file.
            while (true) {
                rc = av_read_frame(fmt_, pkt_);
                if (rc < 0) {
                    avcodec_send_packet(ctx_, nullptr);
                    break;
                }
                bool is_video = pkt_->stream_index == stream_;
                if (is_video) avcodec_send_packet(ctx_, pkt_);
                av_packet_unref(pkt_);
                if (is_video) break;
            }
        }
    }

    void convert(uint8_t* dst) {
        sws_ = sws_getCachedContext(sws_, frame_->width, frame_->height,
                                    static_cast<AVPixelFormat>(frame_->format), width_, height_,
                                    AV_PIX_FMT_RGB24, SWS_BILINEAR, nullptr, nullptr, nullptr);
        uint8_t* planes[4] = {dst, nullptr, nullptr, nullptr};
        int strides[4] = {width_ * 3, 0, 0, 0};
        sws_scale(sws_, frame_->data, frame_->linesize, 0, frame_->height, planes, strides);
    }

    AVFormatContext* fmt_ = nullptr;
    AVCodecContext* ctx_ = nullptr;
    SwsContext* sws_ = nullptr;
    AVPacket* pkt_ = nullptr;
    AVFrame* frame_ = nullptr;
    int stream_ = -1;
    int width_ = 0, height_ = 0;
    double fps_ = 0.0;
    int64_t frame_count_ = 0;
    int64_t index_ = 0;
    bool eof_ = false;
};

}  // namespace

PYBIND11_MODULE(_framedecoder, m) {
    m.doc() = "FFmpeg-backed video frame decoder";
    py::class_<FrameDecoder>(m, "FrameDecoder")
        .def(py::init<const std::string&, int>(), py::arg("path"), py::arg("threads") = 0)
        .def("read", &FrameDecoder::read, "Next frame as (H, W, 3) uint8 RGB, or None at EOF")
        .def("read_into", &FrameDecoder::read_into, py::arg("buffer"),
             "Decode the next frame into an existing (H, W, 3) uint8 array; False at EOF")
        .def("__iter__", [](py::object self) { return self; })
        .def("__next__",
             [](FrameDecoder& d) {
                 py::object f = d.read();
                 if (f.is_none()) throw py::stop_iteration();
                 return f;
             })
        .def_property_readonly("width", &FrameDecoder::width)
        .def_property_readonly("height", &FrameDecoder::height)
        .def_property_readonly("fps", &FrameDecoder::fps)
        .def_property_readonly("frame_count", &FrameDecoder::frame_count)
        .def_property_readonly("index", &FrameDecoder::index);
}

// A small fixed-size thread pool.
//
// The accept loop hands each connected socket to the pool; a worker takes it
// and handles the request. A bounded queue gives back-pressure, which is what
// makes "requests in flight" and latency climb under load instead of the
// process simply falling over.
#pragma once

#include <condition_variable>
#include <cstddef>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

namespace ss {

class ThreadPool {
public:
    explicit ThreadPool(std::size_t workers, std::size_t max_queue)
        : max_queue_(max_queue) {
        if (workers == 0) workers = 1;
        for (std::size_t i = 0; i < workers; ++i) {
            threads_.emplace_back([this] { worker_loop(); });
        }
    }

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    ~ThreadPool() { shutdown(); }

    // Enqueue a job. Returns false if the queue is full (caller should shed
    // the connection) or the pool is shutting down.
    bool submit(std::function<void()> job) {
        {
            std::unique_lock<std::mutex> lock(mutex_);
            if (stopping_ || queue_.size() >= max_queue_) return false;
            queue_.push(std::move(job));
        }
        cv_.notify_one();
        return true;
    }

    void shutdown() {
        {
            std::unique_lock<std::mutex> lock(mutex_);
            if (stopping_) return;
            stopping_ = true;
        }
        cv_.notify_all();
        for (auto& t : threads_) {
            if (t.joinable()) t.join();
        }
        threads_.clear();
    }

    std::size_t worker_count() const { return threads_.size(); }

private:
    void worker_loop() {
        for (;;) {
            std::function<void()> job;
            {
                std::unique_lock<std::mutex> lock(mutex_);
                cv_.wait(lock, [this] { return stopping_ || !queue_.empty(); });
                if (stopping_ && queue_.empty()) return;
                job = std::move(queue_.front());
                queue_.pop();
            }
            job();
        }
    }

    std::vector<std::thread> threads_;
    std::queue<std::function<void()>> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::size_t max_queue_;
    bool stopping_ = false;
};

}  // namespace ss

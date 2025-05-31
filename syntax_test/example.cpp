/**
 * C++ 语法高亮测试文件
 * 演示现代 C++ (C++11/14/17/20) 特性
 * 
 * @author xyanmi
 * @date 2024-03-15
 */

#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <algorithm>
#include <functional>
#include <thread>
#include <mutex>
#include <future>
#include <chrono>
#include <optional>
#include <variant>
#include <type_traits>
#include <concepts>

// 命名空间
namespace QuickServer {

// 模板类
template<typename T>
class SmartArray {
private:
    std::unique_ptr<T[]> data_;
    size_t size_;
    size_t capacity_;
    mutable std::mutex mutex_;

public:
    // 构造函数
    explicit SmartArray(size_t initial_capacity = 10) 
        : data_(std::make_unique<T[]>(initial_capacity))
        , size_(0)
        , capacity_(initial_capacity) {}
    
    // 移动构造函数
    SmartArray(SmartArray&& other) noexcept 
        : data_(std::move(other.data_))
        , size_(other.size_)
        , capacity_(other.capacity_) {
        other.size_ = 0;
        other.capacity_ = 0;
    }
    
    // 移动赋值操作符
    SmartArray& operator=(SmartArray&& other) noexcept {
        if (this != &other) {
            data_ = std::move(other.data_);
            size_ = other.size_;
            capacity_ = other.capacity_;
            other.size_ = 0;
            other.capacity_ = 0;
        }
        return *this;
    }
    
    // 删除拷贝构造和拷贝赋值
    SmartArray(const SmartArray&) = delete;
    SmartArray& operator=(const SmartArray&) = delete;
    
    // 析构函数
    ~SmartArray() = default;
    
    // 添加元素
    void push_back(const T& item) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (size_ >= capacity_) {
            resize(capacity_ * 2);
        }
        data_[size_++] = item;
    }
    
    // 完美转发版本
    template<typename... Args>
    void emplace_back(Args&&... args) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (size_ >= capacity_) {
            resize(capacity_ * 2);
        }
        data_[size_++] = T(std::forward<Args>(args)...);
    }
    
    // 访问元素
    T& operator[](size_t index) {
        if (index >= size_) {
            throw std::out_of_range("Index out of range");
        }
        return data_[index];
    }
    
    const T& operator[](size_t index) const {
        if (index >= size_) {
            throw std::out_of_range("Index out of range");
        }
        return data_[index];
    }
    
    // 获取大小
    [[nodiscard]] size_t size() const noexcept { 
        std::lock_guard<std::mutex> lock(mutex_);
        return size_; 
    }
    
    // 检查是否为空
    [[nodiscard]] bool empty() const noexcept { 
        return size() == 0; 
    }
    
    // 迭代器支持
    class iterator {
    private:
        T* ptr_;
    public:
        explicit iterator(T* ptr) : ptr_(ptr) {}
        
        T& operator*() { return *ptr_; }
        T* operator->() { return ptr_; }
        iterator& operator++() { ++ptr_; return *this; }
        iterator operator++(int) { iterator tmp = *this; ++ptr_; return tmp; }
        bool operator==(const iterator& other) const { return ptr_ == other.ptr_; }
        bool operator!=(const iterator& other) const { return ptr_ != other.ptr_; }
    };
    
    iterator begin() { return iterator(data_.get()); }
    iterator end() { return iterator(data_.get() + size_); }
    
private:
    void resize(size_t new_capacity) {
        auto new_data = std::make_unique<T[]>(new_capacity);
        for (size_t i = 0; i < size_; ++i) {
            new_data[i] = std::move(data_[i]);
        }
        data_ = std::move(new_data);
        capacity_ = new_capacity;
    }
};

// 概念 (C++20)
template<typename T>
concept Printable = requires(T t) {
    std::cout << t;
};

template<typename T>
concept Addable = requires(T a, T b) {
    { a + b } -> std::same_as<T>;
};

// 函数模板与概念
template<Printable T>
void print(const T& value) {
    std::cout << value << std::endl;
}

template<Addable T>
T add(const T& a, const T& b) {
    return a + b;
}

// SFINAE 示例
template<typename T>
typename std::enable_if_t<std::is_arithmetic_v<T>, bool>
is_positive(T value) {
    return value > T{0};
}

// 变参模板
template<typename T>
T sum(T&& t) {
    return std::forward<T>(t);
}

template<typename T, typename... Args>
T sum(T&& t, Args&&... args) {
    return std::forward<T>(t) + sum(std::forward<Args>(args)...);
}

// 类型特征
template<typename T>
struct is_smart_array : std::false_type {};

template<typename T>
struct is_smart_array<SmartArray<T>> : std::true_type {};

template<typename T>
inline constexpr bool is_smart_array_v = is_smart_array<T>::value;

// 枚举类
enum class LogLevel : int {
    DEBUG = 0,
    INFO = 1,
    WARNING = 2,
    ERROR = 3,
    CRITICAL = 4
};

// 强类型包装器
template<typename T, typename Tag>
class StrongType {
private:
    T value_;
    
public:
    explicit StrongType(const T& value) : value_(value) {}
    explicit StrongType(T&& value) : value_(std::move(value)) {}
    
    const T& get() const { return value_; }
    T& get() { return value_; }
    
    // 操作符重载
    bool operator==(const StrongType& other) const {
        return value_ == other.value_;
    }
    
    bool operator<(const StrongType& other) const {
        return value_ < other.value_;
    }
};

// 类型别名
using UserId = StrongType<uint64_t, struct UserIdTag>;
using UserName = StrongType<std::string, struct UserNameTag>;

// 用户类
class User {
private:
    UserId id_;
    UserName name_;
    std::string email_;
    bool is_active_;
    std::chrono::system_clock::time_point created_at_;
    
public:
    User(UserId id, UserName name, std::string email)
        : id_(std::move(id))
        , name_(std::move(name))
        , email_(std::move(email))
        , is_active_(true)
        , created_at_(std::chrono::system_clock::now()) {}
    
    // Getter 方法
    [[nodiscard]] const UserId& id() const noexcept { return id_; }
    [[nodiscard]] const UserName& name() const noexcept { return name_; }
    [[nodiscard]] const std::string& email() const noexcept { return email_; }
    [[nodiscard]] bool is_active() const noexcept { return is_active_; }
    
    // Setter 方法
    void set_active(bool active) noexcept { is_active_ = active; }
    void set_email(std::string new_email) { email_ = std::move(new_email); }
    
    // 获取账户年龄
    [[nodiscard]] std::chrono::days account_age() const {
        auto now = std::chrono::system_clock::now();
        return std::chrono::duration_cast<std::chrono::days>(now - created_at_);
    }
};

// 访问者模式 (std::variant)
using UserAction = std::variant<
    struct Login { std::string ip_address; },
    struct Logout { std::chrono::system_clock::time_point timestamp; },
    struct UpdateProfile { std::string field; std::string new_value; },
    struct DeleteAccount { std::string reason; }
>;

// 访问者函数
struct UserActionVisitor {
    void operator()(const Login& action) {
        std::cout << "User logged in from: " << action.ip_address << std::endl;
    }
    
    void operator()(const Logout& action) {
        auto time_t = std::chrono::system_clock::to_time_t(action.timestamp);
        std::cout << "User logged out at: " << std::ctime(&time_t) << std::endl;
    }
    
    void operator()(const UpdateProfile& action) {
        std::cout << "Profile updated - " << action.field 
                  << ": " << action.new_value << std::endl;
    }
    
    void operator()(const DeleteAccount& action) {
        std::cout << "Account deleted. Reason: " << action.reason << std::endl;
    }
};

// 异步操作
class AsyncUserService {
private:
    std::vector<User> users_;
    mutable std::shared_mutex users_mutex_;
    
public:
    // 异步查找用户
    std::future<std::optional<User>> find_user_async(const UserId& id) const {
        return std::async(std::launch::async, [this, id]() -> std::optional<User> {
            std::shared_lock<std::shared_mutex> lock(users_mutex_);
            
            auto it = std::find_if(users_.begin(), users_.end(),
                [&id](const User& user) {
                    return user.id().get() == id.get();
                });
            
            if (it != users_.end()) {
                return *it;
            }
            return std::nullopt;
        });
    }
    
    // 异步添加用户
    std::future<bool> add_user_async(User user) {
        return std::async(std::launch::async, [this, user = std::move(user)]() -> bool {
            std::unique_lock<std::shared_mutex> lock(users_mutex_);
            
            // 检查用户是否已存在
            auto exists = std::any_of(users_.begin(), users_.end(),
                [&user](const User& existing) {
                    return existing.id().get() == user.id().get();
                });
            
            if (!exists) {
                users_.emplace_back(std::move(user));
                return true;
            }
            return false;
        });
    }
    
    // 批量处理用户
    template<typename Func>
    void for_each_user(Func&& func) const {
        std::shared_lock<std::shared_mutex> lock(users_mutex_);
        std::for_each(users_.begin(), users_.end(), std::forward<Func>(func));
    }
};

// RAII 资源管理
class FileResource {
private:
    std::FILE* file_;
    std::string filename_;
    
public:
    explicit FileResource(const std::string& filename, const std::string& mode = "r")
        : file_(std::fopen(filename.c_str(), mode.c_str()))
        , filename_(filename) {
        if (!file_) {
            throw std::runtime_error("Failed to open file: " + filename);
        }
    }
    
    ~FileResource() {
        if (file_) {
            std::fclose(file_);
        }
    }
    
    // 移动构造函数
    FileResource(FileResource&& other) noexcept
        : file_(other.file_), filename_(std::move(other.filename_)) {
        other.file_ = nullptr;
    }
    
    // 移动赋值
    FileResource& operator=(FileResource&& other) noexcept {
        if (this != &other) {
            if (file_) {
                std::fclose(file_);
            }
            file_ = other.file_;
            filename_ = std::move(other.filename_);
            other.file_ = nullptr;
        }
        return *this;
    }
    
    // 删除拷贝
    FileResource(const FileResource&) = delete;
    FileResource& operator=(const FileResource&) = delete;
    
    std::FILE* get() const { return file_; }
    const std::string& filename() const { return filename_; }
};

} // namespace QuickServer

// 主函数
int main() {
    using namespace QuickServer;
    
    try {
        // 创建智能数组
        SmartArray<int> numbers;
        
        // 添加一些数字
        for (int i = 1; i <= 10; ++i) {
            numbers.push_back(i * i);
        }
        
        // 使用范围 for 循环
        std::cout << "数组内容: ";
        for (const auto& num : numbers) {
            std::cout << num << " ";
        }
        std::cout << std::endl;
        
        // 创建用户
        auto user1 = User(
            UserId(1001),
            UserName("张三"),
            "zhangsan@example.com"
        );
        
        auto user2 = User(
            UserId(1002),
            UserName("李四"),
            "lisi@example.com"
        );
        
        // 异步用户服务
        AsyncUserService service;
        
        // 异步添加用户
        auto future1 = service.add_user_async(std::move(user1));
        auto future2 = service.add_user_async(std::move(user2));
        
        // 等待结果
        bool result1 = future1.get();
        bool result2 = future2.get();
        
        std::cout << "用户添加结果: " << std::boolalpha 
                  << result1 << ", " << result2 << std::endl;
        
        // 查找用户
        auto find_future = service.find_user_async(UserId(1001));
        auto found_user = find_future.get();
        
        if (found_user) {
            std::cout << "找到用户: " << found_user->name().get() 
                      << " (" << found_user->email() << ")" << std::endl;
        }
        
        // 用户操作示例
        std::vector<UserAction> actions = {
            Login{"192.168.1.100"},
            UpdateProfile{"email", "new_email@example.com"},
            Logout{std::chrono::system_clock::now()}
        };
        
        UserActionVisitor visitor;
        for (const auto& action : actions) {
            std::visit(visitor, action);
        }
        
        // 使用概念和函数模板
        print("Hello, C++20!");
        print(42);
        
        auto result = add(10, 20);
        std::cout << "10 + 20 = " << result << std::endl;
        
        // 变参模板求和
        auto total = sum(1, 2, 3, 4, 5);
        std::cout << "1+2+3+4+5 = " << total << std::endl;
        
        // Lambda 表达式
        auto multiply = [](auto a, auto b) { return a * b; };
        std::cout << "Lambda: 6 * 7 = " << multiply(6, 7) << std::endl;
        
        // 智能指针
        auto smart_ptr = std::make_unique<std::string>("智能指针管理的字符串");
        std::cout << "智能指针内容: " << *smart_ptr << std::endl;
        
        std::cout << "\n✅ C++ 语法高亮测试完成!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "错误: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}


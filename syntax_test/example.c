/**
 * QuickServer C语言示例文件
 * 用于测试 C 语言语法高亮功能
 * 
 * @author xyanmi
 * @date 2024-03-15
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>

// 宏定义
#define MAX_BUFFER_SIZE 1024
#define DEFAULT_PORT 8080
#define BACKLOG 10
#define MAX_CLIENTS 100

// 常量定义
const char* HTTP_200_OK = "HTTP/1.1 200 OK\r\n";
const char* HTTP_404_NOT_FOUND = "HTTP/1.1 404 Not Found\r\n";
const char* CONTENT_TYPE_HTML = "Content-Type: text/html\r\n";
const char* CONTENT_TYPE_JSON = "Content-Type: application/json\r\n";

// 结构体定义
typedef struct {
    int socket_fd;
    char client_ip[INET_ADDRSTRLEN];
    int port;
    time_t connect_time;
} client_info_t;

typedef struct {
    char method[16];
    char path[256];
    char version[16];
    char headers[MAX_BUFFER_SIZE];
    char body[MAX_BUFFER_SIZE];
} http_request_t;

typedef struct {
    int status_code;
    char status_message[64];
    char headers[MAX_BUFFER_SIZE];
    char body[MAX_BUFFER_SIZE];
    size_t content_length;
} http_response_t;

// 全局变量
static int server_socket = -1;
static volatile int server_running = 1;
static client_info_t clients[MAX_CLIENTS];
static int client_count = 0;

// 函数声明
int create_server_socket(int port);
void handle_client_connection(int client_socket, struct sockaddr_in* client_addr);
int parse_http_request(const char* raw_request, http_request_t* request);
void build_http_response(http_response_t* response, int status_code, 
                        const char* content_type, const char* body);
void send_http_response(int client_socket, const http_response_t* response);
void serve_static_file(int client_socket, const char* file_path);
void handle_api_request(int client_socket, const http_request_t* request);
void cleanup_and_exit(int signal);
void log_message(const char* level, const char* format, ...);

/**
 * 创建服务器套接字
 * @param port 监听端口
 * @return 服务器套接字文件描述符，失败返回-1
 */
int create_server_socket(int port) {
    int sockfd;
    struct sockaddr_in server_addr;
    int opt = 1;
    
    // 创建套接字
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket creation failed");
        return -1;
    }
    
    // 设置套接字选项
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt failed");
        close(sockfd);
        return -1;
    }
    
    // 配置服务器地址
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);
    
    // 绑定地址
    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind failed");
        close(sockfd);
        return -1;
    }
    
    // 开始监听
    if (listen(sockfd, BACKLOG) < 0) {
        perror("listen failed");
        close(sockfd);
        return -1;
    }
    
    log_message("INFO", "Server listening on port %d", port);
    return sockfd;
}

/**
 * 处理客户端连接
 * @param client_socket 客户端套接字
 * @param client_addr 客户端地址信息
 */
void handle_client_connection(int client_socket, struct sockaddr_in* client_addr) {
    char buffer[MAX_BUFFER_SIZE];
    http_request_t request;
    ssize_t bytes_received;
    
    // 获取客户端IP地址
    char client_ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &(client_addr->sin_addr), client_ip, INET_ADDRSTRLEN);
    
    log_message("INFO", "New connection from %s:%d", 
                client_ip, ntohs(client_addr->sin_port));
    
    // 接收HTTP请求
    memset(buffer, 0, sizeof(buffer));
    bytes_received = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_received <= 0) {
        log_message("ERROR", "Failed to receive data from client");
        close(client_socket);
        return;
    }
    
    buffer[bytes_received] = '\0';
    log_message("DEBUG", "Received request:\n%s", buffer);
    
    // 解析HTTP请求
    if (parse_http_request(buffer, &request) != 0) {
        log_message("ERROR", "Failed to parse HTTP request");
        close(client_socket);
        return;
    }
    
    // 路由处理
    if (strncmp(request.path, "/api/", 5) == 0) {
        handle_api_request(client_socket, &request);
    } else {
        serve_static_file(client_socket, request.path);
    }
    
    close(client_socket);
}

/**
 * 解析HTTP请求
 * @param raw_request 原始请求字符串
 * @param request 解析后的请求结构体
 * @return 成功返回0，失败返回-1
 */
int parse_http_request(const char* raw_request, http_request_t* request) {
    char* line;
    char* request_copy;
    char* saveptr;
    
    if (!raw_request || !request) {
        return -1;
    }
    
    // 复制请求字符串
    request_copy = strdup(raw_request);
    if (!request_copy) {
        return -1;
    }
    
    // 解析请求行
    line = strtok_r(request_copy, "\r\n", &saveptr);
    if (!line) {
        free(request_copy);
        return -1;
    }
    
    // 解析方法、路径和版本
    if (sscanf(line, "%15s %255s %15s", 
               request->method, request->path, request->version) != 3) {
        free(request_copy);
        return -1;
    }
    
    // 解析请求头和请求体
    strcpy(request->headers, "");
    strcpy(request->body, "");
    
    int in_headers = 1;
    while ((line = strtok_r(NULL, "\r\n", &saveptr)) != NULL) {
        if (strlen(line) == 0) {
            in_headers = 0;
            continue;
        }
        
        if (in_headers) {
            if (strlen(request->headers) + strlen(line) + 2 < MAX_BUFFER_SIZE) {
                strcat(request->headers, line);
                strcat(request->headers, "\n");
            }
        } else {
            if (strlen(request->body) + strlen(line) + 1 < MAX_BUFFER_SIZE) {
                strcat(request->body, line);
            }
        }
    }
    
    free(request_copy);
    return 0;
}

/**
 * 构建HTTP响应
 * @param response 响应结构体
 * @param status_code 状态码
 * @param content_type 内容类型
 * @param body 响应体
 */
void build_http_response(http_response_t* response, int status_code, 
                        const char* content_type, const char* body) {
    const char* status_message;
    
    // 设置状态消息
    switch (status_code) {
        case 200: status_message = "OK"; break;
        case 404: status_message = "Not Found"; break;
        case 500: status_message = "Internal Server Error"; break;
        default: status_message = "Unknown"; break;
    }
    
    response->status_code = status_code;
    strcpy(response->status_message, status_message);
    
    // 构建响应头
    snprintf(response->headers, sizeof(response->headers),
             "HTTP/1.1 %d %s\r\n"
             "%s\r\n"
             "Content-Length: %zu\r\n"
             "Connection: close\r\n"
             "Server: QuickServer/1.0\r\n"
             "\r\n",
             status_code, status_message,
             content_type ? content_type : "",
             strlen(body));
    
    // 设置响应体
    strcpy(response->body, body);
    response->content_length = strlen(body);
}

/**
 * 发送HTTP响应
 * @param client_socket 客户端套接字
 * @param response 响应结构体
 */
void send_http_response(int client_socket, const http_response_t* response) {
    ssize_t bytes_sent;
    
    // 发送响应头
    bytes_sent = send(client_socket, response->headers, 
                     strlen(response->headers), 0);
    if (bytes_sent < 0) {
        log_message("ERROR", "Failed to send response headers");
        return;
    }
    
    // 发送响应体
    if (response->content_length > 0) {
        bytes_sent = send(client_socket, response->body, 
                         response->content_length, 0);
        if (bytes_sent < 0) {
            log_message("ERROR", "Failed to send response body");
            return;
        }
    }
    
    log_message("INFO", "Response sent: %d %s (%zu bytes)",
                response->status_code, response->status_message,
                response->content_length);
}

/**
 * 主函数
 */
int main(int argc, char* argv[]) {
    int port = DEFAULT_PORT;
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    int client_socket;
    
    // 解析命令行参数
    if (argc > 1) {
        port = atoi(argv[1]);
        if (port <= 0 || port > 65535) {
            fprintf(stderr, "Invalid port number: %s\n", argv[1]);
            return EXIT_FAILURE;
        }
    }
    
    // 设置信号处理
    signal(SIGINT, cleanup_and_exit);
    signal(SIGTERM, cleanup_and_exit);
    
    // 创建服务器套接字
    server_socket = create_server_socket(port);
    if (server_socket < 0) {
        fprintf(stderr, "Failed to create server socket\n");
        return EXIT_FAILURE;
    }
    
    printf("🚀 QuickServer started successfully!\n");
    printf("📁 Serving files from current directory\n");
    printf("🌐 Server listening on http://localhost:%d\n", port);
    printf("💡 Press Ctrl+C to stop the server\n\n");
    
    // 主循环：接受客户端连接
    while (server_running) {
        client_socket = accept(server_socket, 
                              (struct sockaddr*)&client_addr, 
                              &client_addr_len);
        
        if (client_socket < 0) {
            if (errno == EINTR) {
                continue;  // 被信号中断，继续循环
            }
            perror("accept failed");
            break;
        }
        
        // 处理客户端连接（简化版，实际项目中应该使用多线程或异步处理）
        handle_client_connection(client_socket, &client_addr);
    }
    
    cleanup_and_exit(0);
    return EXIT_SUCCESS;
}

/**
 * 清理并退出
 * @param signal 信号值
 */
void cleanup_and_exit(int signal) {
    server_running = 0;
    
    if (server_socket >= 0) {
        close(server_socket);
        server_socket = -1;
    }
    
    printf("\n👋 QuickServer stopped gracefully.\n");
    
    if (signal != 0) {
        exit(EXIT_SUCCESS);
    }
} 
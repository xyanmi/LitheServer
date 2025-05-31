/**
 * TypeScript 语法高亮测试文件
 * 演示 TypeScript 的高级特性
 */

// 类型定义
type User = {
    id: number;
    name: string;
    email: string;
    isActive: boolean;
    roles: Role[];
    metadata?: Record<string, any>;
};

interface Role {
    id: string;
    name: string;
    permissions: Permission[];
}

enum Permission {
    READ = 'read',
    WRITE = 'write',
    DELETE = 'delete',
    ADMIN = 'admin'
}

// 泛型类型
interface ApiResponse<T> {
    data: T;
    status: 'success' | 'error';
    message?: string;
    timestamp: Date;
}

// 联合类型和字面量类型
type Theme = 'light' | 'dark' | 'auto';
type Status = 'loading' | 'success' | 'error' | 'idle';

// 类定义
class UserService {
    private readonly apiUrl: string = '/api/users';
    private cache = new Map<string, User>();

    constructor(
        private readonly httpClient: HttpClient,
        private readonly logger: Logger
    ) {}

    // 异步方法
    async fetchUser(id: number): Promise<ApiResponse<User>> {
        try {
            const cacheKey = `user-${id}`;
            
            // 检查缓存
            if (this.cache.has(cacheKey)) {
                const cachedUser = this.cache.get(cacheKey)!;
                return {
                    data: cachedUser,
                    status: 'success',
                    timestamp: new Date()
                };
            }

            // 发起API请求
            const response = await this.httpClient.get<User>(`${this.apiUrl}/${id}`);
            
            // 缓存结果
            this.cache.set(cacheKey, response.data);
            
            return {
                data: response.data,
                status: 'success',
                timestamp: new Date()
            };
        } catch (error) {
            this.logger.error('Failed to fetch user:', error);
            throw new UserServiceError(`Failed to fetch user ${id}`, error);
        }
    }

    // 方法重载
    createUser(userData: Omit<User, 'id'>): Promise<User>;
    createUser(name: string, email: string): Promise<User>;
    async createUser(
        userDataOrName: Omit<User, 'id'> | string,
        email?: string
    ): Promise<User> {
        let userData: Omit<User, 'id'>;
        
        if (typeof userDataOrName === 'string') {
            userData = {
                name: userDataOrName,
                email: email!,
                isActive: true,
                roles: []
            };
        } else {
            userData = userDataOrName;
        }

        const response = await this.httpClient.post<User>(this.apiUrl, userData);
        return response.data;
    }

    // 使用条件类型
    updateUser<T extends keyof User>(
        id: number,
        field: T,
        value: User[T]
    ): Promise<User> {
        return this.httpClient.patch<User>(`${this.apiUrl}/${id}`, {
            [field]: value
        }).then(response => response.data);
    }
}

// 自定义错误类
class UserServiceError extends Error {
    constructor(
        message: string,
        public readonly cause?: Error,
        public readonly code: string = 'USER_SERVICE_ERROR'
    ) {
        super(message);
        this.name = 'UserServiceError';
    }
}

// 工具类型使用
type PartialUser = Partial<User>;
type RequiredUser = Required<User>;
type UserEmail = Pick<User, 'email'>;
type UserWithoutId = Omit<User, 'id'>;

// 高阶组件类型
type WithLoading<T> = T & { isLoading: boolean };
type WithError<T> = T & { error?: string };

// 函数类型
type EventHandler<T = Event> = (event: T) => void;
type AsyncFunction<T, R> = (param: T) => Promise<R>;

// 装饰器
function log(target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const method = descriptor.value;
    
    descriptor.value = function (...args: any[]) {
        console.log(`Calling ${propertyName} with args:`, args);
        const result = method.apply(this, args);
        console.log(`Result:`, result);
        return result;
    };
}

function validate(validator: (value: any) => boolean) {
    return function (target: any, propertyName: string) {
        let value: any;
        
        const getter = () => value;
        const setter = (newValue: any) => {
            if (!validator(newValue)) {
                throw new Error(`Invalid value for ${propertyName}: ${newValue}`);
            }
            value = newValue;
        };
        
        Object.defineProperty(target, propertyName, {
            get: getter,
            set: setter,
            enumerable: true,
            configurable: true
        });
    };
}

// 使用装饰器的类
class UserModel {
    @validate((value: string) => value.length > 0)
    name!: string;

    @validate((value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))
    email!: string;

    @log
    save(): boolean {
        // 保存逻辑
        return true;
    }
}

// 条件类型
type NonNullable<T> = T extends null | undefined ? never : T;

// 映射类型
type ReadonlyUser = {
    readonly [K in keyof User]: User[K];
};

type OptionalUser = {
    [K in keyof User]?: User[K];
};

// 模板字面量类型
type EventName<T extends string> = `on${Capitalize<T>}`;
type UserEvent = EventName<'click' | 'hover' | 'focus'>;

// 模块和命名空间
namespace Utils {
    export function debounce<T extends (...args: any[]) => any>(
        fn: T,
        delay: number
    ): (...args: Parameters<T>) => void {
        let timeoutId: NodeJS.Timeout;
        
        return (...args: Parameters<T>) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn(...args), delay);
        };
    }

    export function throttle<T extends (...args: any[]) => any>(
        fn: T,
        limit: number
    ): (...args: Parameters<T>) => void {
        let inThrottle: boolean;
        
        return (...args: Parameters<T>) => {
            if (!inThrottle) {
                fn(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// 使用示例
const userService = new UserService(new HttpClient(), new Logger());

// 异步操作
async function main() {
    try {
        const userResponse = await userService.fetchUser(1);
        console.log('User:', userResponse.data);
        
        const newUser = await userService.createUser('John Doe', 'john@example.com');
        console.log('Created user:', newUser);
        
        const updatedUser = await userService.updateUser(1, 'name', 'Jane Doe');
        console.log('Updated user:', updatedUser);
        
    } catch (error) {
        if (error instanceof UserServiceError) {
            console.error('User service error:', error.message, error.code);
        } else {
            console.error('Unexpected error:', error);
        }
    }
}

// React 组件类型示例
interface ComponentProps {
    title: string;
    children: React.ReactNode;
    onClick?: EventHandler<React.MouseEvent>;
}

const MyComponent: React.FC<ComponentProps> = ({ title, children, onClick }) => {
    const [count, setCount] = React.useState<number>(0);
    const [theme, setTheme] = React.useState<Theme>('light');
    
    const debouncedOnClick = React.useMemo(
        () => onClick ? Utils.debounce(onClick, 300) : undefined,
        [onClick]
    );
    
    return (
        <div className={`component theme-${theme}`} onClick={debouncedOnClick}>
            <h1>{title}</h1>
            <p>Count: {count}</p>
            <button onClick={() => setCount(prev => prev + 1)}>
                Increment
            </button>
            {children}
        </div>
    );
};

export { UserService, UserServiceError, Utils };
export type { User, Role, Permission, ApiResponse, Theme };



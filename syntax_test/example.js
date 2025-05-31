/**
 * JavaScript 语法高亮测试文件
 * 演示现代 JavaScript (ES6+) 语法特性
 */

// 导入和导出
import { fetchData, processData } from './utils.js';
import React, { useState, useEffect } from 'react';

// 常量定义
const API_BASE_URL = 'https://api.example.com';
const MAX_RETRIES = 3;

// 类定义 (ES6 Class)
class DataManager {
    #privateField = 'private data'; // 私有字段
    
    constructor(config = {}) {
        this.config = {
            timeout: 5000,
            retries: MAX_RETRIES,
            ...config  // 展开操作符
        };
        this.cache = new Map();
        this.listeners = new Set();
    }
    
    // Getter 和 Setter
    get cacheSize() {
        return this.cache.size;
    }
    
    set timeout(value) {
        if (typeof value !== 'number' || value < 0) {
            throw new Error('Timeout must be a positive number');
        }
        this.config.timeout = value;
    }
    
    // 异步方法
    async fetchData(url, options = {}) {
        const fullUrl = `${API_BASE_URL}/${url}`;
        
        try {
            // 模板字符串和箭头函数
            const response = await fetch(fullUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getToken()}`
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.cache.set(url, data);
            return data;
            
        } catch (error) {
            console.error(`Failed to fetch data from ${fullUrl}:`, error);
            throw error;
        }
    }
    
    // 生成器函数
    *generateData(count) {
        for (let i = 0; i < count; i++) {
            yield {
                id: i,
                timestamp: Date.now(),
                random: Math.random()
            };
        }
    }
    
    getToken() {
        return localStorage.getItem('authToken') ?? 'default-token';
    }
}

// 箭头函数和高阶函数
const processArray = (arr, processor) => arr
    .filter(item => item != null)
    .map(processor)
    .reduce((acc, val) => acc + val, 0);

// 解构赋值
const { name, age, ...rest } = { 
    name: 'John', 
    age: 30, 
    city: 'New York', 
    country: 'USA' 
};

// Promise 和异步处理
const handleAsyncOperation = async () => {
    try {
        const results = await Promise.allSettled([
            fetch('/api/users'),
            fetch('/api/posts'),
            fetch('/api/comments')
        ]);
        
        const [users, posts, comments] = results.map(result => 
            result.status === 'fulfilled' ? result.value : null
        );
        
        return { users, posts, comments };
        
    } catch (error) {
        console.error('Async operation failed:', error);
        return null;
    }
};

// React Hooks 示例
const UserComponent = ({ userId }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        let mounted = true;
        
        const fetchUser = async () => {
            try {
                setLoading(true);
                const userData = await fetchData(`users/${userId}`);
                
                if (mounted) {
                    setUser(userData);
                    setError(null);
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message);
                    setUser(null);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };
        
        fetchUser();
        
        // 清理函数
        return () => {
            mounted = false;
        };
    }, [userId]);
    
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;
    if (!user) return <div>No user found</div>;
    
    return (
        <div className="user-card">
            <h2>{user.name}</h2>
            <p>Email: {user.email}</p>
            <p>Joined: {new Date(user.createdAt).toLocaleDateString()}</p>
        </div>
    );
};

// 正则表达式
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/;

// 验证函数
const validateForm = ({ email, phone, password }) => {
    const errors = {};
    
    if (!emailRegex.test(email)) {
        errors.email = 'Invalid email format';
    }
    
    if (!phoneRegex.test(phone)) {
        errors.phone = 'Invalid phone format';
    }
    
    if (password.length < 8) {
        errors.password = 'Password must be at least 8 characters';
    }
    
    return {
        isValid: Object.keys(errors).length === 0,
        errors
    };
};

// 工具函数
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// 模块导出
export {
    DataManager,
    processArray,
    handleAsyncOperation,
    UserComponent,
    validateForm,
    debounce
};

export default DataManager;

// 立即执行函数表达式 (IIFE)
(function() {
    'use strict';
    
    console.log('Module loaded successfully!');
    
    // 测试代码
    const manager = new DataManager();
    const testData = [...manager.generateData(5)];
    
    console.log('Generated test data:', testData);
})(); 
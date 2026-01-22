# 幸运飞艇开奖查询工具

## 使用说明

### 1. 启动代理服务器（必须）

由于浏览器的CORS跨域限制，需要先启动代理服务器：

```bash
python proxy_server.py
```

代理服务器默认运行在 `http://localhost:8888`

如果需要使用其他端口，可以指定：
```bash
python proxy_server.py 9999
```

### 2. 打开HTML文件

在浏览器中打开 `index.html` 文件即可使用。

### 3. 功能说明

- **信用盘查询**：从信用盘API获取开奖数据
- **官方盘查询**：从官方盘API获取开奖数据，或手动输入文本数据
- **定位胆预测**：
  - 算法预测：基于历史数据的频率、遗漏、趋势分析
  - AI预测：使用DeepSeek AI进行智能预测（需要API Token）

### 注意事项

1. **必须先启动代理服务器**，否则会出现CORS跨域错误
2. 代理服务器需要保持运行状态
3. DeepSeek AI预测功能需要有效的API Token

## 文件说明

- `index.html` - 主程序文件（HTML + CSS + JavaScript）
- `proxy_server.py` - 代理服务器（解决CORS问题）
- `定制1.py` - 原始Python版本（参考）

## 故障排除

### 查询失败：Failed to fetch

**原因**：代理服务器未启动或CORS跨域问题

**解决方法**：
1. 确保代理服务器正在运行（`python proxy_server.py`）
2. 检查代理服务器端口是否为8888
3. 如果使用其他端口，需要修改 `index.html` 中的 `PROXY_SERVER` 变量

### 代理服务器无法启动

**可能原因**：
1. 端口被占用
2. 缺少Python依赖库

**解决方法**：
1. 使用其他端口：`python proxy_server.py 9999`
2. 安装依赖：`pip install requests`


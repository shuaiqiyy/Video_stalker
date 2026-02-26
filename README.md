# Video_stalker

## 功能说明

实时监控视频流媒体软件日志，当检测到设备开始观看视频时，在Windows右下角弹出通知提醒"请注意"。

## 核心特性

| 特性 | 说明 |
|------|------|
| 智能监控 | 自动检测`AtHomeVideoStreamer.exe`进程启动后开始监控 |
| 自动识别 | 自动查找`log`文件夹中数字最大的`ich_run_X.log`文件 |
| 无感运行 | 静默后台运行，无控制台窗口，无日志输出 |
| 不占资源 | 不持续占用日志文件，原软件可正常写入 |
| 去重提醒 | 同一设备3秒内不重复通知，支持多通道独立提醒 |

## 使用方法

### 方式一：直接运行（默认配置）

```bash
python main.py
```

### 方式二：自定义参数

```bash
python log_monitor.py <进程名> <日志目录>
```

示例：

```bash
python log_monitor.py myapp.exe "c:\Program Files\MyApp\log"
```

### 方式三：开机自启动
首次运行时自动添加到开机启动项，后续开机自动后台运行。

取消开机启动：

删除注册表项 ```HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\LogMonitor```

## 通知效果

触发条件： 日志中出现

```plain
Create Channel PeerCid is XXXXX, ServiceID is Y, ChanId[Z]
```

弹出提示：
```plain
请注意
设备 XXXX 通道Z 开始观看
```

## 系统要求
Windows 10 / Windows 11

Python 3.7+

## 注意事项

退出方法： 在任务管理器中结束python.exe进程

日志轮转： 自动检测日志文件重置，重新定位读取位置

## 技术细节
使用tasklist检测进程状态

使用glob匹配最新日志文件

使用qt显示通知

文件读取采用"打开-读取-关闭"模式，不持有文件句柄

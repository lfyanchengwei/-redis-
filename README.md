运行效果：
![image](https://github.com/user-attachments/assets/a03b9088-7693-4dd8-848d-edc7e6648463)

课程项目总结报告
——日志采集与可视化监控系统

​一、项目概述​
本项目设计并实现了一套实时日志监控系统，用于模拟多设备环境下的日志采集、分析与可视化展示。系统支持动态展示各设备的异常比例（WARN/ERROR）、历史错误记录及告警信息，最终以仪表盘形式提供直观的监控界面。

​二、系统架构与功能模块​

​程序结构​

log-monitor-system/

├── log_producers/      # 多节点日志采集（多进程模拟）  

├── analyzer_service/   # 统计分析与告警生成（微服务架构）  

└── visualization/      # 可视化Web界面（实时图表展示）  

​技术选型​

​核心技术栈​

​日志采集​：Python Multiprocessing 模拟多节点

​消息队列​：Redis Pub/Sub 实现异步通信

​分析服务​：动态滑动窗口统计（最近N条日志）

​可视化​：Flask + Socket.IO 实时数据推送，ECharts 动态图表

​辅助工具​

配置文件：Python Config 模块

日志处理：datetime / json 格式标准化

​三、实现细节​

​日志生成模块​

​模拟设备​：每个采集节点生成带时间戳、设备ID、日志等级的自定义日志

​频率控制​：以100ms/条的速度持续向Redis广播

​统计分析模块​

​核心指标​：

短时错误率（ERROR比例超过50%触发告警）

最近10次ERROR事件追踪

​数据结构​：采用双端队列（deque）维护时间窗口

​可视化模块​

​前端功能点​：

设备选择下拉菜单（动态绑定设备列表）

颜色标记机制（ERROR-红色，WARN-黄色）

数据滚动更新（保留最近50个数据点）

​后端通信​：通过WebSocket向浏览器推送实时状态

​四、项目亮点​

​解耦设计​：日志采集、分析与展示模块完全解耦，支持横向扩展

​实时性优化​：利用Redis高频消息吞吐能力，数据延迟<200ms

​容错机制​：日志解析异常自动跳过，关键字段丢失时触发警报

​五、不足与改进方向​

​待优化点​：

当前采用轮询分析策略，未来可优化为事件驱动模式

告警规则单一，需支持自定义阈值配置

历史数据未持久化，无法回溯长期趋势

​扩展计划​：

增加用户权限管理与告警邮件推送

集成ELK技术栈提升日志检索能力

​六、总结与收获​

通过本项目，深入理解了分布式日志监控系统的核心设计原理，掌握了跨进程通信（Redis）、动态数据可视化（ECharts）等实用技术。同时，面对构建实时系统时的并发处理、数据一致性等问题，通过实际调试积累了宝贵的工程经验。

# 实验二：OSPF 单区域路由配置

## 1. 实验目的
- 掌握 OSPF 协议的基本工作原理。
- 掌握单区域 OSPF 的配置方法。
- 学会查看 OSPF 邻居状态和路由表。

## 2. 实验原理
OSPF（Open Shortest Path First）是基于链路状态的内部网关协议。它通过 Dijkstra 算法计算最短路径。OSPF 网络必须有一个骨干区域（Area 0），所有非骨干区域必须与 Area 0 相连。

## 3. 实验步骤

### 步骤 1：配置接口 IP
首先为路由器接口配置 IP 地址，并确保直连链路连通。

```bash
RouterA(config)# interface g0/0
RouterA(config-if)# ip address 192.168.1.1 255.255.255.0
RouterA(config-if)# no shutdown
```

### 步骤 2：启用 OSPF 进程
在路由器上启用 OSPF，进程号（Process ID）本地有效，不同路由器可以不同。

```bash
RouterA(config)# router ospf 1
```

### 步骤 3：宣告网段
使用 `network` 命令宣告属于该 OSPF 区域的网段。注意使用**反掩码（Wildcard Mask）**。

```bash
RouterA(config-router)# network 192.168.1.0 0.0.0.255 area 0
RouterA(config-router)# network 10.0.0.0 0.0.0.3 area 0
```

### 步骤 4：验证配置
查看 OSPF 邻居建立情况，状态为 `FULL` 表示邻接关系建立成功。

```bash
RouterA# show ip ospf neighbor
```

查看路由表，标记为 `O` 的条目即为 OSPF 学习到的路由。

```bash
RouterA# show ip route
```

## 4. 常见问题
**Q: OSPF 邻居卡在 2WAY 或 EXSTART 状态怎么办？**
A: 
1. 检查两端接口的 MTU 是否一致。
2. 检查 Hello 时间和 Dead 时间是否一致（默认 Hello=10s）。
3. 检查区域 ID（Area ID）是否匹配。
4. 检查认证密码（如有配置）是否一致。
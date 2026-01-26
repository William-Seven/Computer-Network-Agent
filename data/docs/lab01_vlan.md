# 实验一：VLAN 基础配置与划分

## 1. 实验目的
- 理解虚拟局域网（VLAN）的基本概念和作用。
- 掌握在交换机上创建 VLAN、划分端口的方法。
- 掌握 Trunk 链路的配置方法，实现跨交换机的 VLAN 通信。

## 2. 实验原理
VLAN（Virtual Local Area Network）即虚拟局域网，是将一个物理的 LAN 在逻辑上划分成多个广播域的通信技术。VLAN 内的主机间可以直接通信，而 VLAN 间的主机通信必须通过三层路由设备。

## 3. 实验步骤

### 步骤 1：创建 VLAN
在交换机 SwitchA 上创建 VLAN 10 和 VLAN 20。

```bash
SwitchA> enable
SwitchA# configure terminal
SwitchA(config)# vlan 10
SwitchA(config-vlan)# name Sales
SwitchA(config-vlan)# exit
SwitchA(config)# vlan 20
SwitchA(config-vlan)# name Engineer
SwitchA(config-vlan)# exit
```

### 步骤 2：将端口划入 VLAN
将接口 FastEthernet 0/1 划分到 VLAN 10，接口 0/2 划分到 VLAN 20。

```bash
SwitchA(config)# interface fa0/1
SwitchA(config-if)# switchport mode access
SwitchA(config-if)# switchport access vlan 10
SwitchA(config-if)# exit

SwitchA(config)# interface fa0/2
SwitchA(config-if)# switchport mode access
SwitchA(config-if)# switchport access vlan 20
SwitchA(config-if)# exit
```

### 步骤 3：配置 Trunk 链路
如果两台交换机之间需要传输多个 VLAN 的数据，需要将连接端口配置为 Trunk 模式。

```bash
SwitchA(config)# interface fa0/24
SwitchA(config-if)# switchport mode trunk
SwitchA(config-if)# switchport trunk allowed vlan all
```

## 4. 常见问题
**Q: 为什么划分 VLAN 后，不同 VLAN 的 PC 无法 ping 通？**
A: 这是正常现象。VLAN 的主要作用就是隔离广播域。不同 VLAN 属于不同的逻辑子网，它们之间的通信需要通过路由器或三层交换机进行路由（单臂路由或 SVI 接口）。
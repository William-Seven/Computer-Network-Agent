# 实验三：NAT 网络地址转换配置

## 1. 实验目的
- 理解私有 IP 与公有 IP 的区别。
- 掌握静态 NAT、动态 NAT 和 PAT（端口多路复用）的配置。

## 2. 实验原理
NAT（Network Address Translation）用于将内部私有网络地址转换为外部公有网络地址，解决 IPv4 地址枯竭问题。最常用的是 PAT（NAPT），允许多个内网主机共享一个公网 IP 上网。

## 3. 实验步骤

### 步骤 1：定义内外网接口
首先需要指定哪些接口属于内部网络（Inside），哪些属于外部网络（Outside）。

```bash
Router(config)# interface g0/0
Router(config-if)# ip nat inside
Router(config-if)# exit

Router(config)# interface g0/1
Router(config-if)# ip nat outside
Router(config-if)# exit
```

### 步骤 2：配置 ACL 定义允许转换的流量
创建标准 ACL，匹配允许上网的内网网段（例如 192.168.10.0/24）。

```bash
Router(config)# access-list 1 permit 192.168.10.0 0.0.0.255
```

### 步骤 3：配置 PAT (Overload)
将匹配 ACL 1 的流量转换为出接口 g0/1 的公网 IP，关键关键字是 `overload`。

```bash
Router(config)# ip nat inside source list 1 interface g0/1 overload
```

### 步骤 4：验证 NAT
在内网 PC 上 Ping 外网地址，并在路由器上查看 NAT 转换表。

```bash
Router# show ip nat translations
```

## 4. 常见问题
**Q: 配置了 NAT 但还是上不了网？**
A: 
1. 检查 ACL 是否正确匹配了源 IP。
2. 检查 inside 和 outside 接口方向是否配置正确。
3. 检查路由器是否配置了缺省路由指向 ISP（`ip route 0.0.0.0 0.0.0.0 <Next-Hop>`）。
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class TopologyAnalyzer:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("MODEL_API_BASE")
        model_name = os.getenv("MODEL_NAME")
        if api_key:
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.1,  # 使用较低的温度以保证分析逻辑严谨
                openai_api_base=base_url,
                openai_api_key=api_key
            )
        else:
            self.llm = None

    def analyze(self, topology_text: str) -> str:
        if not self.llm:
            return "❌ 系统未配置大模型密钥，无法进行拓扑分析。"

        if not topology_text or len(topology_text.strip()) < 10:
            return "❌ 提供的拓扑文本过短，无法分析。"

        # 严格的系统提示词
        system_prompt = """
你是一个资深的思科(Cisco)网络系统架构师和 Dynamips 仿真专家。
你的任务是解析用户提供的网络拓扑配置文本（如含有 [[router R1]], f0/0 = SW1 f1/1 等格式），并完成以下两项任务：

### 任务 1：绘制物理拓扑图
必须严格使用 Mermaid 的 `graph TD` 语法绘制出设备的物理连接图。
为了最大程度避免线条交叉，让网络拓扑更加层次分明，请务必遵守以下高级排布指令：
1. **采用ELK引擎引擎**：在 markdown 代码块内，`graph TD` 的上一行，必须严格加上这句魔法指令：`%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%`。
2. **逻辑分层与集中声明**：为了让拓扑图上下对称，请首先“集中声明”所有的设备节点（先统一声明所有的路由器节点，接着声明所有交换机节点，最后声明所有 PC 节点），然后再统一定义它们之间的连线！
3. **同层对齐辅助**：对于处于相同网络层级的设备（如两个平行的核心路由器 R1、R2，或两台相邻的电脑 PC1、PC2），你可以使用不可见连线（例如 `R1 ~~~ R2`、`PC1 ~~~ PC2`）来强行阻止它们相互纠缠。
4. **准确区分设备类型并赋予精美颜色配色（极其重要）**：
   请在 mermaid 图代码的最后（或者任何不报错的地方）加入这三行全局主题定义以美化图表视角：
   `classDef router fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e293b;`
   `classDef switch fill:#dcfce7,stroke:#059669,stroke-width:2px,color:#1e293b;`
   `classDef pc fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#1e293b;`
   通过【设备名特征】准确区分并强制在声明节点时附带class类型（使用 `:::` 语法绑定）：
   - 所有设备的开头都是[[router，区别在于后半部分
   - 名字以 `R` 开头（如 `R100`）：路由器，使用圆形并绑定类：`R100(("R100")):::router`
   - 名字以 `SW` 开头（如 `SW1`）：交换机，使用矩形并绑定类：`SW1["SW1"]:::switch`
   - 名字以 `PC` 开头（如 `PC100`）：个人电脑，使用圆角矩形并绑定类：`PC100("PC100"):::pc`
   - 绝不能仅仅看到 `[[router PC100]]` 就把它当成路由器！
5. 所有的物理连线请不要使用带箭头的实线，请使用 `---`。并且必须双向标注接口，例如：`R1 -- "f0/0 -- f1/11" --- SW1`。不要在连线上写特殊字符导致语法报错。

### 任务 2：静态连通性检查报告
在输出完 Mermaid 代码库之后，你需要对配置逻辑进行深度的一致性体检：
1. **统计信息**：一共有多少台路由器、交换机、PC？
2. **逻辑核对**：检查所有连线是否“对称匹配”。以及接口命名是否规范（例如 `s1/0`、`f0/0` 这种格式）。
3. **接口规范**：检查是否存在常见笔误（例如 S 口连 F 口、端口超过该设备插槽最大限制等）。

### 任务 3：输出修正后的拓扑文件
如果你在“任务 2”中检查出了任何连线不对称、拼写错误或逻辑漏洞，请在体检报告的最下方，为你输出一份**修正后的 Dynamips 拓扑配置脚本文本**，请将其包裹在 ```text 代码块中。如果你认为学生的配置完全正确没有任何问题，则明确写出一句：“配置逻辑严密完全正确，无需修改源代码。”

### 输出格式要求与排版规范（重要）：
1. 必须先输出 Mermaid 图形（包裹在 ```mermaid 代码块内），然后再输出 Markdown 格式的中文体检报告。永远不要在输出中附带“任务一”、“任务二”、“任务三”这种分步标题，直接流畅自然地输出可视化结果和文字报告。
2. **Markdown高级排版美学**：报告中请适当使用 Markdown 元素。
3. **严禁在文本中使用波浪号 `~` 表示接口或数字范围**（如 `s1/0~s1/3` 或 `0~3` 会导致 Markdown 错误渲染极长的删除线）。请务必使用“到”或中划线“-”来表示范围（例如 `s1/0 到 s1/3`，`0 到 3`）。
4. 提及设备名称或具体接口时，请习惯用反引号包裹以增加可读性（如 `R100` 的 `s1/0` 接口）。
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析以下网络拓扑脚本：\n\n{topology_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"❌ 在调用大模型分析时发生错误：{str(e)}"

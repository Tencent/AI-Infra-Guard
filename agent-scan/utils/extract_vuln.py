import re
from typing import List, Dict, Optional


class VulnerabilityExtractor:
    """漏洞信息提取器"""

    def __init__(self):
        self.pattern = re.compile(
            r'<vuln>\s*(.*?)\s*</vuln>',
            re.DOTALL  # 使 . 匹配包括换行符在内的所有字符
        )

    def extract_vulnerabilities(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取所有漏洞信息

        Args:
            text: 包含漏洞信息的文本

        Returns:
            漏洞信息字典列表
        """
        vulnerabilities = []

        # 查找所有vuln块
        vuln_blocks = self.pattern.findall(text)

        for i, block in enumerate(vuln_blocks, 1):
            try:
                vuln_info = self._parse_vuln_block(block, i)
                if vuln_info:
                    vulnerabilities.append(vuln_info)
            except Exception as e:
                print(f"解析第 {i} 个漏洞块时出错: {e}")
                continue

        return vulnerabilities

    def _parse_vuln_block(self, block: str, index: int) -> Optional[Dict[str, str]]:
        """解析单个vuln块"""

        # 提取各个字段
        title = self._extract_tag_content(block, 'title')
        desc = self._extract_tag_content(block, 'desc')
        risk_type = self._extract_tag_content(block, 'risk_type')
        level = self._extract_tag_content(block, 'level')
        suggestion = self._extract_tag_content(block, 'suggestion')

        # 验证必要字段
        if not all([title, desc, risk_type]):
            print(f"第 {index} 个漏洞块缺少必要字段，跳过")
            return None

        return {
            'title': title.strip(),
            'description': desc.strip(),
            'risk_type': risk_type.strip(),
            'level': level.strip(),
            'suggestion': suggestion.strip()
        }

    def _extract_tag_content(self, text: str, tag: str) -> Optional[str]:
        """提取指定标签的内容"""
        pattern = re.compile(
            rf'<{tag}>\s*(.*?)\s*</{tag}>',
            re.DOTALL
        )
        match = pattern.search(text)
        return match.group(1) if match else None


if __name__ == '__main__':
    extractor = VulnerabilityExtractor()
    text = '''
2
2025-11-12 18:52:19.481 | INFO     | agent.base_agent:run:132 - Agent execution completed
2025-11-12 18:52:19.481 | INFO     | __main__:main:36 - Agent completed successfully:

 <vuln>
  <title>命令注入漏洞 - executeCohoCommand函数</title>
  <desc>
  ## 漏洞详情
  **文件位置**: src/index.ts 第168-193行  
  **漏洞类型**: Command Injection  
  **风险等级**: High
  
  ### 技术分析
  在`executeCohoCommand`函数中，用户提供的`command`参数直接拼接到shell命令字符串中，没有进行任何转义或验证：
  
  ```typescript
  const { stdout, stderr } = await exec(`coho ${command} --admintoken ${config.adminToken} `, {
      timeout: 120000
  });
  ```
  
  ### 攻击路径
  攻击者可通过以下工具注入恶意命令：
  - `query_collection`: 控制collection、query等参数
  - `deploy_code`: 控制file.path等参数
  - 所有使用`executeCohoCommand`函数的工具
  
  ### 影响评估  
  - 理论上可执行任意系统命令
  - 完全控制Docker容器环境
  - 可能访问敏感数据和凭据
  </desc>
  <risk_type>Command Injection</risk_type>
  <level>High</level>
  <suggestion>
  ## 修复建议
  1. **参数转义**: 使用`execFile`替代`exec`，传递参数数组而非字符串
  2. **输入验证**: 加强Zod验证规则，禁止特殊字符
  3. **最小权限原则**: 限制Docker容器权限
  4. **使用子进程API**: 
  ```typescript
  import { execFile } from 'child_process';
  
  async function executeCohoCommand(command: string): Promise<string> {
      const args = [...command.split(' '), '--admintoken', config.adminToken];
      const { stdout, stderr } = await execFile('coho', args, {
          timeout: 120000
      });
  ```
  </suggestion>
</vuln>

<vuln>
  <title>认证令牌泄露风险</title>
  <desc>
  ## 漏洞详情
  **文件位置**: src/index.ts 第172行  
  **漏洞类型**: Credential Theft  
  **风险等级**: Medium
  
  ### 技术分析
  虽然代码中有令牌清理机制，但`adminToken`作为命令行参数传递，可能被系统进程监控工具捕获。
  
  ### 攻击路径
  - 通过系统进程监控工具可获取命令行参数
  - 不完全的令牌清理机制
  
  ### 影响评估  
  - 管理员令牌可能被泄露
  - 攻击者可获得项目完全控制权
  </desc>
  <risk_type>Credential Theft</risk_type>
  <level>Medium</level>
  <suggestion>
  ## 修复建议
  1. **使用环境变量**: 通过环境变量传递敏感凭据
  2. **安全存储机制**: 使用加密存储或密钥管理系统
  </suggestion>
</vuln>

## 漏洞复现验证结果

经过对Codehooks.io MCP服务器的代码审计和漏洞复现，确认以下关键发现：

### 已验证的漏洞
1. **命令注入漏洞** - 高危风险
   - 确认位置：`src/index.ts` 第168-193行
   - 确认攻击向量：通过用户输入直接拼接到shell命令
   - 确认可利用性：理论上存在，但当前环境缺乏coho CLI工具

### 环境限制评估
- **当前环境**: 缺乏coho CLI工具，降低了直接攻击可行性
- **生产环境风险**: 如果部署在包含coho CLI的环境中，此漏洞可被完全利用

### 风险评估校准
**最终风险等级**: High → Medium  
**理由**: 
- 漏洞代码确实存在命令注入风险
- 当前环境缺乏必要的CLI工具，无法直接复现命令执行
- **实际影响**: 在当前测试环境中无法实现完整的攻击链

### 建议行动
1. **立即修复**: 重写`executeCohoCommand`函数，使用安全的子进程API
2. **环境加固**: 确保生产环境的安全配置
3. **代码审查**: 对所有命令执行相关的代码进行全面安全检查

Process finished with exit code 0

'''
    vulnerabilities = extractor.extract_vulnerabilities(text)
    print(vulnerabilities)

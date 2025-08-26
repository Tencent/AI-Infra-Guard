# WorkDir
AIG-PromptSecurity/

# 提取翻译字符串
```bash
# 提取临时文件指令
xgettext --from-code=UTF-8 --keyword=translated_msg  -d messages -o cli/locales/messages.pot cli_run.py cli/red_team_runner.py deepteam/red_teamer/red_teamer.py deepteam/attacks/attack_simulator/attack_simulator.py
# 补充msgstr
```

# 更新翻译字符串
```bash
# 提取指令
xgettext --from-code=UTF-8 --keyword=translated_msg  -d messages -o cli/locales/messages_new.pot cli_run.py cli/red_team_runner.py deepteam/red_teamer/red_teamer.py deepteam/attacks/attack_simulator/attack_simulator.py
# 合并指令
msgmerge --update --backup=none cli/locales/messages.pot cli/locales/messages_new.pot
```

# 生成翻译资源文件
```bash
# 生成.po指令
msginit --locale=zh_CN.UTF-8 --input=cli/locales/messages.pot --output-file=cli/locales/zh_CN/LC_MESSAGES/messages.po
# 生成.mo指令
msgfmt cli/locales/zh_CN/LC_MESSAGES/messages.po -o cli/locales/zh_CN/LC_MESSAGES/messages.mo
```
# 操作指南

## 提交子模块

先将生成的架构子仓库提交到`github`远程

在本仓库中添加子模块：

```bash
# 用标准方式登记 submodule（--force 可复用你 .gitmodules 里的同名条目）
git submodule add -f -b master https://github.com/Cruise-z/<repo>.git \
  VSCode/Python/CodeWM_AutoTest/1_Availability/DT/codeGen/MetaGPT/workspace/<project>/<language>/<repo>
```

然后正常提交即可
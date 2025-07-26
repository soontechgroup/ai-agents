# GCP 自动部署配置指南

## 前提条件

1. GCP 服务器已安装 Miniconda（路径：`/opt/miniconda3`）
2. 服务器上已安装 Git
3. 项目代码部署在 `/root/ai-agents` 目录

## GitHub Secrets 配置

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加以下密钥：

### GCP_SSH_KEY
- **说明**: SSH 私钥，用于 GitHub Actions 连接到 GCP 服务器
- **配置步骤**:

1. **生成 SSH 密钥对**（在本地或任意位置）:
   ```bash
   ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f github_deploy_key
   ```

2. **在 GCP 控制台添加公钥**:
   - 进入 GCP Console → Compute Engine → 元数据
   - 选择 "SSH 密钥" 标签
   - 点击 "添加 SSH 密钥"
   - 复制公钥内容（`cat github_deploy_key.pub`）
   - 用户名设置为 `root`
   - 保存

3. **在 GitHub 添加 Secret**:
   - 复制私钥内容：
     ```bash
     cat github_deploy_key
     ```
   - 进入 GitHub 仓库 → Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - Name: `GCP_SSH_KEY`
   - Secret: 粘贴完整的私钥内容（包括 BEGIN 和 END 行）
   - 点击 "Add secret"

- **注意**: 确保复制完整的私钥内容，包括：
  ```
  -----BEGIN RSA PRIVATE KEY-----
  [密钥内容]
  -----END RSA PRIVATE KEY-----
  ```


## 部署流程

1. 推送代码到 main 分支或合并 PR
2. GitHub Actions 自动触发部署
3. 通过 SSH 连接到服务器（IP 地址已在 `.github/workflows/deploy.yml` 中配置）
4. 拉取最新代码
5. 激活 conda 环境
6. 执行 `./scripts/run.sh restart` 重启服务
7. 本地健康检查确认服务正常运行

## 故障排查

### 查看部署日志
在 GitHub Actions 页面查看工作流运行日志

### 查看服务器应用日志
```bash
ssh root@your-gcp-ip
cd /root/ai-agents
tail -f logs/app.log
```

### 手动重启服务
```bash
cd /root/ai-agents
./scripts/run.sh restart
```

## 安全建议

1. 定期更换 SSH 密钥
2. 限制 GitHub Secrets 的访问权限
3. 使用防火墙限制 SSH 访问
4. 考虑使用 GCP 的 Identity-Aware Proxy
5. 生产环境配置文件不要提交到代码仓库
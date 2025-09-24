#!/bin/bash

# -----------------------------------------------------------------------------
# 一键部署脚本
#
# 功能:
# 1. 检查并安装 Docker 和 Docker Compose。
# 2. 从 Git 仓库下载应用。
# 3. 创建独立的发布包目录。
# 4. 使用 Docker Compose 启动应用。
# -----------------------------------------------------------------------------

# 设置颜色变量以便输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 当任何命令失败时立即退出脚本
set -e
# 管道命令中任何一个失败，则整个管道视为失败
set -o pipefail

# --- 配置变量 ---
GIT_URL="https://github.com/Tencent/AI-Infra-Guard.git"
REPO_NAME="AI-Infra-Guard"
RELEASE_DIR="release-package"
# 可以修改为您需要的 Docker Compose 版本
COMPOSE_VERSION="v2.24.6"

IMAGE_AGENT="zhuquelab/aig-agent:latest"
IMAGE_SERVER="zhuquelab/aig-server:latest"

# --- 函数定义 ---

# 打印信息
info() {
    echo -e "${YELLOW}[INFO] $1${NC}"
}

# 打印成功信息
success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# 打印错误信息并退出
error_exit() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# 检查命令是否存在
command_exists() {
    command -v "$1" &> /dev/null
}

# 检查并安装 Docker
install_docker() {
    if command_exists docker; then
        success "Docker 已安装。版本信息: $(docker --version)"
    else
        info "未检测到 Docker，正在尝试安装..."
        if ! curl -fsSL https://get.docker.com | bash -s docker; then
            error_exit "Docker 安装失败。请检查网络或手动安装。"
        fi

        info "正在启动并设置 Docker 开机自启..."
        if ! systemctl enable --now docker; then
            error_exit "无法启动或设置 Docker 开机自启。请检查 systemd 状态。"
        fi
        success "Docker 安装并启动成功！"
    fi
}

# 检查并安装 Docker Compose
install_docker_compose() {
    if command_exists docker-compose; then
        success "Docker Compose 已安装。版本信息: $(docker-compose --version)"
    else
        info "未检测到 Docker Compose，正在尝试安装版本 ${COMPOSE_VERSION}..."

        # 检查系统架构
        DOCKER_COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)"

        info "正在从 ${DOCKER_COMPOSE_URL} 下载..."
        if ! curl -L "${DOCKER_COMPOSE_URL}" -o /usr/local/bin/docker-compose; then
            error_exit "Docker Compose 下载失败。请检查网络或 GitHub Release 页面。"
        fi

        if ! chmod +x /usr/local/bin/docker-compose; then
            error_exit "为 Docker Compose 添加执行权限失败。"
        fi

        success "Docker Compose 安装成功！版本信息: $(docker-compose --version)"
    fi
}

# 部署应用
deploy_application() {
    info "开始部署应用..."

    # 检查是否存在旧的目录，并询问用户是否删除
    if [ -d "${REPO_NAME}" ] || [ -d "${RELEASE_DIR}" ]; then
        info "检测到已存在的目录 (${REPO_NAME} 或 ${RELEASE_DIR})。"
        read -p "是否要删除这些目录并重新部署? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            info "正在删除旧目录..."
            rm -rf "${REPO_NAME}" "${RELEASE_DIR}"
            success "旧目录已删除。"
        else
            error_exit "用户取消操作。部署中止。"
        fi
    fi

    # 1. 克隆仓库
    info "正在从 ${GIT_URL} 克隆仓库..."
    if ! git clone "${GIT_URL}"; then
        error_exit "Git 克隆失败。请检查 Git URL 或网络连接。"
    fi
    success "仓库克隆成功。"

    # 2. 创建发布目录并复制文件
    info "正在创建发布目录: ${RELEASE_DIR}"
    mkdir -p "${RELEASE_DIR}"/{db,log,uploads}

    info "正在复制必要文件到 ${RELEASE_DIR}..."
    # 进入源仓库目录以简化复制路径
    cd "${REPO_NAME}"

    cp docker-compose.images.yml "../${RELEASE_DIR}/docker-compose.yml"
    cp -r data "../${RELEASE_DIR}/data"
    cp README.md "../${RELEASE_DIR}/README.md"
    cp README_ZH.md "../${RELEASE_DIR}/README_ZH.md"
    cp CHANGELOG.md "../${RELEASE_DIR}/CHANGELOG.md"

    # 返回上级目录
    cd ..
    success "文件复制完成。"

    # 3. 清理原始仓库
    info "正在清理临时文件..."
    rm -rf "${REPO_NAME}"
    success "临时文件清理完毕。"

    # 4. 检测并删除原有容器
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_AGENT$"; then
        info "检测到旧Agent容器，正在删除..."
        docker rmi "$IMAGE_AGENT"
    fi

    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$IMAGE_SERVER$"; then
            info "检测到旧Server容器，正在删除..."
            docker rmi "$IMAGE_SERVER"
    fi

    # 4. 启动 Docker Compose
    cd "${RELEASE_DIR}"
    info "当前目录: $(pwd)"
    info "正在使用 docker-compose 启动服务 (后台模式)..."
    if ! docker-compose pull; then
        error_exit "docker-compose 拉取镜像失败。请检查网络。"
    fi
    if ! docker-compose up -d; then
        error_exit "docker-compose 启动失败。请使用 'docker-compose logs' 查看错误日志。"
    fi

    success "应用部署并启动成功！"
}

# --- 主函数 ---
main() {
    # 检查是否为 root 用户
    if [ "$(id -u)" -ne 0 ]; then
       error_exit "此脚本需要 root 权限运行。请使用 'sudo bash $0' 执行。"
    fi

    # 检查核心依赖
    command_exists git || error_exit "请先安装 'git'。"
    command_exists curl || error_exit "请先安装 'curl'。"

    # 执行流程
    install_docker
    install_docker_compose
    deploy_application

    # 结束提示
    echo
    success "=========================================================="
    success "         所有操作已成功完成！"
    success "=========================================================="
    info "应用正在后台运行中。"
    info "您可以使用 'cd ${RELEASE_DIR}' 进入应用目录。"
    info "查看服务状态: ${YELLOW}docker-compose ps${NC}"
    info "查看实时日志: ${YELLOW}docker-compose logs -f${NC}"
    info "停止并移除容器: ${YELLOW}docker-compose down${NC}"
    echo
}

# --- 脚本入口 ---
main

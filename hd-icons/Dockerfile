FROM python:3.9-slim
MAINTAINER xiaodi, mail:d_songbo@126.com

# 安装 git 和 Pillow 依赖
RUN apt-get update && apt-get install -y git libjpeg-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制文件
COPY . .

# 创建 icons 文件夹
RUN mkdir -p /app/icons

# 指定默认映射路径值和端口值
VOLUME /app/icons
EXPOSE 50560

CMD ["python", "app.py"]
# 构建阶段：VITE_API_BASE_URL 必须在构建时传入（Sealos 后端公网根地址，无尾斜杠）
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

ARG VITE_AMAP_KEY=
ENV VITE_AMAP_KEY=${VITE_AMAP_KEY}
ARG VITE_AMAP_SECURITY_JSCODE=
ENV VITE_AMAP_SECURITY_JSCODE=${VITE_AMAP_SECURITY_JSCODE}

RUN npm run build

# 运行阶段：静态资源由 Nginx 提供
FROM nginx:1.26-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

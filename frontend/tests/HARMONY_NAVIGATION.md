# 鸿蒙导航兼容性验证

## 2026-10-08 真机反馈和修订依据

用户截图显示高德 Android 下载落地页和 HarmonyOS NEXT 拒绝安装提示；
用户已安装鸿蒙版高德。下载提示不能用作“高德未安装”的判断。
截图中的浏览器界面包含百度图标，尚未确认其具体名称和版本。

上一版只验证了 URI 参数和前端逻辑，未证明网页可以唤起手机 App。
高德官方 HarmonyOS NEXT 文档示例是原生 `startAbility` 调用：
https://lbs.amap.com/api/amap-mobile/guide/harmony-os/route-next

本次直接检查了高德线上 H5 源码与关联配置：

- https://m.amap.com/service/combo/?f=common/callnativeSchemas.js
  `getNaviByXYNSchema` 构造 `amapuri://route/plan?`，不带末尾斜杠。
- https://m.amap.com/service/combo/?f=common/callnativeMethods.js
  `callByAppLink` 使用 `/applink/?schema=<完整 URI 编码>`；
  `callBySchema` 对非 iOS 浏览器使用隐藏 iframe。
- https://m.amap.com/service/combo/?f=common/callnativeOs.js
  使用 ArkWeb 标识识别鸿蒙浏览器。
- https://m.amap.com/.well-known/applinking.json
  返回鸿蒙应用关联 JSON；只能证明域名已发布关联配置，不能证明每个
  已安装的高德版本均注册了 `/applink/` 路由或能正确处理其中的 URI。

因此 HTTPS 应用链接和 iframe 方案均需要手机验证。HTTPS 入口本身的
网页脚本未完整适配鸿蒙；依赖系统应用链接接管，不将 HTTP 200 当作
唤起成功。若关联未被接管，应返回本页面尝试“其他方式打开”。

网页版单独使用 `callnative=0`，关闭自动唤起；iOS/Android 原有入口继续
使用 `callnative=1`。备用协议入口没有下载重定向，超时提示不判断安装状态。

## 自动检查

在仓库根目录运行：

```powershell
node --test frontend/tests/amapNavigation.test.mjs
node --test frontend/tests/browserDrivingRoute.test.mjs
```

在 frontend 目录运行 `npm run build`。测试覆盖平台识别、坐标与中文名称
编码、HTTPS 内层 URI、保留 iOS 行为、定位失败、请求过期、iframe 复用和
清理、未确认唤起反馈、页面隐藏后的反馈。模拟页面隐藏不能证明 App 已启动。

## 手机验收

1. 使用已安装鸿蒙版高德的手机，在当前浏览器和系统浏览器分别测试。
2. 选择预设点，打开导航，允许定位后点“打开高德地图”。
3. 确认打开的是已有 App，且终点名称、经纬度与选中预设点一致。
4. 若 HTTPS 入口未被系统接管，返回后尝试“其他方式打开”。
5. 协议唤起未成功时应留在本页显示反馈，不跳转安卓下载地址。
6. “打开网页版”不应自动发起 App 唤起；“复制目的地”可用于手动导航。
7. 拒绝定位、关闭弹窗、切换目的地时不能使用旧请求的起点或终点。
8. iOS 复验原有导航入口。

## 浏览器路线规划与入口可见性

备用入口直接放在目的地选择区下方，不再折叠于“导航未打开”中；鸿蒙弹窗
内的同名协议按钮在定位阶段可见但禁用，避免定位失败时整个入口消失。
已修改本地源码的按钮在生产站点可见仍需要部署对应前端版本。

按用户要求，页面已取消“浏览器路线规划”按钮及对应路线面板、页面处理逻辑和 Driving 插件加载。独立路线解析模块及其单元测试暂保留，页面不再提供该功能。

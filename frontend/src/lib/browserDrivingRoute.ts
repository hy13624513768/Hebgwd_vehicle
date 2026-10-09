export interface RoutePosition { lng: number; lat: number }
export interface BrowserDrivingRoute {
  origin: RoutePosition
  distance: number
  duration: number
  path: [number, number][]
  steps: { instruction: string; distance: number }[]
}

/** AMap.Geolocation and AMap.Driving both use GCJ-02; browser GPS alone does not. */
export function planBrowserDrivingRoute(amap: any, geolocation: any, destination: RoutePosition): Promise<BrowserDrivingRoute> {
  return new Promise((resolve, reject) => {
    if (!amap?.Driving || !geolocation) {
      reject(new Error('路线规划未就绪，请稍后重试。'))
      return
    }
    geolocation.getCurrentPosition((status: string, result: any) => {
      const lng = Number(result?.position?.lng)
      const lat = Number(result?.position?.lat)
      if (status !== 'complete' || !Number.isFinite(lng) || !Number.isFinite(lat)
        || Math.abs(lng) > 180 || Math.abs(lat) > 90) {
        reject(new Error('无法获取当前位置，请允许浏览器定位后重试。'))
        return
      }
      try {
        // Do not give Driving a map: drawing only after the caller's stale-request
        // check prevents a late result from drawing a route to an old destination.
        const driving = new amap.Driving({ policy: amap.DrivingPolicy?.LEAST_TIME })
        driving.search([lng, lat], [destination.lng, destination.lat], (routeStatus: string, routeResult: any) => {
          const route = routeResult?.routes?.[0]
          if (routeStatus !== 'complete' || !route?.steps?.length) {
            reject(new Error('未能规划驾车路线，请确认目的地可驾车到达后重试。'))
            return
          }
          const path: [number, number][] = []
          for (const step of route.steps) {
            for (const point of step.path ?? []) {
              const x = Number(Array.isArray(point) ? point[0] : point.getLng?.() ?? point.lng)
              const y = Number(Array.isArray(point) ? point[1] : point.getLat?.() ?? point.lat)
              if (Number.isFinite(x) && Number.isFinite(y) && Math.abs(x) <= 180 && Math.abs(y) <= 90) path.push([x, y])
            }
          }
          if (path.length < 2) {
            reject(new Error('路线数据不完整，请重新规划。'))
            return
          }
          resolve({
            origin: { lng, lat },
            distance: Number(route.distance) || 0,
            duration: Number(route.time) || 0,
            path,
            steps: route.steps.map((step: any) => ({
              instruction: String(step.instruction || step.road || '沿路线行驶'),
              distance: Number(step.distance) || 0,
            })),
          })
        })
      } catch {
        reject(new Error('路线规划服务暂时不可用，请稍后重试。'))
      }
    })
  })
}

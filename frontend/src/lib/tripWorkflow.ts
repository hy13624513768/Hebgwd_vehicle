/** 与后端 trip_service.TRANSITIONS 对应；最终权限和状态由后端校验。 */
export const tripTransitions: Record<string, string[]> = {
  pending: ['approved', 'rejected', 'cancelled'],
  approved: ['in_progress', 'cancelled'],
  in_progress: ['completed', 'cancelled'],
  completed: [], rejected: [], cancelled: [],
}

import { http } from './http'

export const stockChecksApi = {
  list(params = {}) {
    return http.get('/stock-checks', { params })
  },
  get(id) {
    return http.get(`/stock-checks/${id}`)
  },
  create(payload) {
    return http.post('/stock-checks', payload)
  },
  update(id, payload) {
    return http.put(`/stock-checks/${id}`, payload)
  },
  submit(id) {
    return http.post(`/stock-checks/${id}/submit`)
  },
  remove(id) {
    return http.delete(`/stock-checks/${id}`)
  }
}

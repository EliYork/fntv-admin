export interface ApiSuccess<T> {
  success: true
  data: T
  message: string
}

export interface ApiFailure {
  success: false
  error: {
    code: string
    message: string
  }
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure

export interface PageData<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  pages: number
  error?: string
}


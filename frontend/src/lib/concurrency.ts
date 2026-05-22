/**
 * Returns a limiter that runs at most `limit` async operations concurrently.
 * Callers beyond the limit queue and execute as slots free.
 */
export function createConcurrencyLimiter(limit: number) {
  let running = 0
  const queue: Array<() => void> = []

  return function run<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const execute = () => {
        running++
        fn()
          .then(resolve, reject)
          .finally(() => {
            running--
            queue.shift()?.()
          })
      }

      if (running < limit) {
        execute()
      } else {
        queue.push(execute)
      }
    })
  }
}

/** Shared limiter for all dashboard API requests.
 *  Concurrency controlled by VITE_API_CONCURRENCY (default: 3). */
const concurrency = Number(import.meta.env.VITE_API_CONCURRENCY) || 3
export const dashboardLimiter = createConcurrencyLimiter(concurrency)

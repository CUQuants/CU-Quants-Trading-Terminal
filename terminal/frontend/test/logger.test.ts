/**
 * Logger Test Suite
 * Test the logging system to ensure it's working correctly
 */

import { logger, apiLogger, wsLogger, uiLogger } from '../src/utils/logger'

console.log('='.repeat(80))
console.log('LOGGER TEST SUITE')
console.log('='.repeat(80))

// Test 1: Basic logging
console.log('\n--- Test 1: Basic Logging ---')
logger.debug('Test', 'This is a DEBUG message', { data: 'test' })
logger.info('Test', 'This is an INFO message', { data: 'test' })
logger.warn('Test', 'This is a WARN message', { data: 'test' })
logger.error('Test', 'This is an ERROR message', { data: 'test' })

// Test 2: Category loggers
console.log('\n--- Test 2: Category Loggers ---')
apiLogger.info('Testing API logger', { endpoint: '/test' })
wsLogger.info('Testing WebSocket logger', { connection: 'test' })
uiLogger.info('Testing UI logger', { component: 'Test' })

// Test 3: Data objects
console.log('\n--- Test 3: Complex Data Objects ---')
const complexData = {
  user: 'test_user',
  timestamp: Date.now(),
  nested: {
    level1: {
      level2: {
        value: 'deep nested value'
      }
    }
  },
  array: [1, 2, 3, 4, 5],
  boolean: true,
  null: null,
  undefined: undefined
}
logger.info('Test', 'Complex data object', complexData)

// Test 4: Errors
console.log('\n--- Test 4: Error Objects ---')
try {
  throw new Error('Test error message')
} catch (error) {
  logger.error('Test', 'Caught an error', error)
}

// Test 5: Log history
console.log('\n--- Test 5: Log History ---')
const history = logger.getHistory()
console.log(`Total logs in history: ${history.length}`)
console.log('First log:', history[0])
console.log('Last log:', history[history.length - 1])

// Test 6: Export logs
console.log('\n--- Test 6: Export Logs ---')
const exported = logger.exportLogs()
console.log('Exported logs (first 200 chars):', exported.substring(0, 200) + '...')

// Test 7: Log levels in different environments
console.log('\n--- Test 7: Environment Detection ---')
console.log('Is Development:', import.meta.env.DEV)
console.log('Is Production:', import.meta.env.PROD)
console.log('Mode:', import.meta.env.MODE)
logger.debug('Test', 'This DEBUG log should only appear in development')

// Test 8: Multiple rapid logs (performance test)
console.log('\n--- Test 8: Performance Test (100 rapid logs) ---')
const startTime = performance.now()
for (let i = 0; i < 100; i++) {
  logger.info('Performance', `Log ${i}`, { index: i })
}
const endTime = performance.now()
console.log(`Time taken: ${(endTime - startTime).toFixed(2)}ms`)

// Test 9: Clear history
console.log('\n--- Test 9: Clear History ---')
console.log('Logs before clear:', logger.getHistory().length)
logger.clearHistory()
console.log('Logs after clear:', logger.getHistory().length)

// Test 10: Re-populate and check limit
console.log('\n--- Test 10: Log Limit Test (1100 logs) ---')
for (let i = 0; i < 1100; i++) {
  logger.info('Limit', `Log ${i}`)
}
console.log('Logs in history (should be max 1000):', logger.getHistory().length)

console.log('\n' + '='.repeat(80))
console.log('ALL TESTS COMPLETED')
console.log('='.repeat(80))
console.log('\nCheck the console above for color-coded logs.')
console.log('Open the Debug Panel (Ctrl+Shift+D) to see the visual interface.')
console.log('='.repeat(80))

<template>
  <div>
    <!-- 参数配置 -->
    <div class="card">
      <h2>⚙️ 完整回测参数</h2>
      <div class="form-grid">
        <div class="form-group">
          <label>币种</label>
          <select v-model="symbol">
            <option value="ETH/USDT">ETH/USDT</option>
            <option value="BTC/USDT">BTC/USDT</option>
            <option value="SOL/USDT">SOL/USDT</option>
          </select>
        </div>
        <div class="form-group">
          <label>回测天数</label>
          <input v-model.number="days" type="number" min="1" max="365">
        </div>
        <div class="form-group">
          <label>初始资金</label>
          <input v-model.number="initialCapital" type="number" step="100">
        </div>
        <div class="form-group">
          <label>杠杆倍数</label>
          <select v-model.number="leverage">
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="3">3x</option>
            <option value="5">5x</option>
            <option value="10">10x</option>
          </select>
        </div>
      </div>
      
      <div class="button-group">
        <button class="btn-primary" @click="runBacktest" :disabled="loading">
          {{ loading ? '回测中...' : '🚀 开始完整回测' }}
        </button>
      </div>
      
      <div v-if="message" :class="['message', message.type, 'active']">
        {{ message.text }}
      </div>
    </div>

    <!-- 策略对比结果 -->
    <div v-if="result" class="card">
      <h2>📊 策略对比结果</h2>
      <div class="comparison-grid">
        <div v-for="(strategy, name) in result.strategies" :key="name" class="comparison-card">
          <h3>{{ getStrategyName(name) }}</h3>
          <div class="strategy-stats">
            <div class="stat-item">
              <span class="label">总收益率:</span>
              <span class="value" :class="strategy.total_return >= 0 ? 'positive' : 'negative'">
                {{ formatPercent(strategy.total_return) }}
              </span>
            </div>
            <div class="stat-item">
              <span class="label">最终资金:</span>
              <span class="value">${{ formatNumber(strategy.final_capital) }}</span>
            </div>
            <div class="stat-item">
              <span class="label">交易次数:</span>
              <span class="value">{{ strategy.total_trades }}</span>
            </div>
            <div class="stat-item">
              <span class="label">胜率:</span>
              <span class="value">{{ formatPercent(strategy.win_rate) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 权益曲线对比 -->
    <div v-if="result" class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2>📈 权益曲线对比</h2>
        <button @click="debugChart" style="padding: 0.5rem 1rem; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
          调试图表
        </button>
      </div>
      <div class="chart-container" ref="equityChartContainer">
        <p style="text-align: center; color: #666; margin-top: 150px;">正在加载图表...</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const symbol = ref('ETH/USDT')
    const initialCapital = ref(10000)
    const days = ref(90)
    const leverage = ref(1.0)
    const loading = ref(false)
    const result = ref(null)
    const message = ref(null)
    const equityChartContainer = ref(null)
    let chart = null

    const runBacktest = async () => {
      loading.value = true
      message.value = null

      try {
        const requestBody = {
          symbol: symbol.value,
          initial_capital: initialCapital.value,
          days: days.value,
          leverage: leverage.value,
          funding_rate: 0.0,
          funding_interval: 8,
          auto_calculate_range: true
        }

        const response = await fetch('/api/backtest/run', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody)
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || '回测失败')
        }
        
        const data = await response.json()
        result.value = data
        
        updateChart()
        message.value = { type: 'success', text: '✅ 完整回测完成' }
      } catch (error) {
        console.error('Backtest error:', error)
        message.value = { type: 'error', text: `❌ 错误: ${error.message}` }
      } finally {
        loading.value = false
      }
    }

    const waitForChart = () => {
      return new Promise((resolve) => {
        if (typeof Chart !== 'undefined') {
          console.log('Chart.js is available for FullBacktest')
          resolve()
          return
        }
        
        let attempts = 0
        const maxAttempts = 100
        
        const checkChart = () => {
          attempts++
          if (typeof Chart !== 'undefined') {
            console.log('Chart.js loaded for FullBacktest after', attempts, 'attempts')
            resolve()
          } else if (attempts >= maxAttempts) {
            console.error('Chart.js failed to load for FullBacktest after 5 seconds')
            resolve()
          } else {
            setTimeout(checkChart, 50)
          }
        }
        checkChart()
      })
    }

    const updateChart = async () => {
      console.log('=== FullBacktest updateChart Debug Start ===')
      console.log('1. Container:', equityChartContainer.value)
      console.log('2. Result:', result.value)
      console.log('3. Strategies:', result.value?.strategies)
      console.log('4. Chart.js available:', typeof Chart !== 'undefined')
      
      if (!equityChartContainer.value) {
        console.error('❌ Container element not found')
        return
      }

      if (!result.value?.strategies) {
        console.error('❌ No strategies data')
        return
      }

      if (typeof Chart === 'undefined') {
        console.error('❌ Chart.js not loaded')
        equityChartContainer.value.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: #f44336; background: #ffebee; border-radius: 8px;">
            <h4>Chart.js 未加载</h4>
            <p>请检查网络连接并刷新页面</p>
          </div>
        `
        return
      }

      // 销毁现有图表
      if (chart) {
        console.log('3. Destroying existing chart')
        chart.destroy()
        chart = null
      }

      try {
        console.log('4. Creating canvas element')
        
        // 清空容器
        equityChartContainer.value.innerHTML = ''
        
        // 创建canvas
        const canvas = document.createElement('canvas')
        canvas.width = 800
        canvas.height = 400
        canvas.style.width = '100%'
        canvas.style.height = '400px'
        equityChartContainer.value.appendChild(canvas)
        
        console.log('5. Canvas created:', canvas)
        
        // 获取2D上下文
        const ctx = canvas.getContext('2d')
        console.log('6. Context:', ctx)

        // 获取第一个策略的时间戳作为标签
        const firstStrategy = Object.values(result.value.strategies)[0]
        const timestamps = firstStrategy.timestamps || []
        
        console.log('7. Timestamps length:', timestamps.length)

        // 创建标签
        let labels = []
        if (timestamps.length > 0) {
          labels = timestamps.map((ts, index) => {
            if (index % Math.ceil(timestamps.length / 10) === 0) {
              const date = new Date(ts)
              return date.toLocaleDateString('zh-CN')
            }
            return ''
          })
        } else {
          // 如果没有时间戳，使用索引
          const maxLength = Math.max(...Object.values(result.value.strategies).map(s => s.equity_curve?.length || 0))
          labels = Array.from({length: maxLength}, (_, i) => `${i + 1}`)
        }

        console.log('8. Labels created:', labels.length)

        // 检测主题
        const isDark = document.querySelector('.dark-theme') !== null
        const textColor = isDark ? '#e1f5fe' : '#333'
        const gridColor = isDark ? 'rgba(0, 188, 212, 0.2)' : 'rgba(0, 0, 0, 0.1)'

        console.log('9. Theme detected:', isDark ? 'dark' : 'light')

        // 创建数据集
        const datasets = []
        const colors = {
          long: isDark ? '#4caf50' : '#10b981',
          short: isDark ? '#f44336' : '#ef4444',
          neutral: isDark ? '#00e5ff' : '#3b82f6'
        }

        Object.entries(result.value.strategies).forEach(([strategyName, strategyData]) => {
          console.log(`10. Adding dataset for ${strategyName}:`, strategyData.equity_curve?.length)
          if (strategyData.equity_curve && strategyData.equity_curve.length > 0) {
            datasets.push({
              label: getStrategyName(strategyName),
              data: strategyData.equity_curve,
              borderColor: colors[strategyName] || '#007bff',
              backgroundColor: (colors[strategyName] || '#007bff') + '20',
              borderWidth: 2,
              fill: false,
              tension: 0.1,
              pointRadius: 0,
              pointHoverRadius: 4
            })
          }
        })

        console.log('11. Datasets created:', datasets.length)

        if (datasets.length === 0) {
          throw new Error('没有可用的策略数据')
        }

        // 创建图表配置
        const config = {
          type: 'line',
          data: {
            labels: labels,
            datasets: datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // 禁用动画以避免问题
            plugins: {
              legend: {
                display: true,
                position: 'top',
                labels: {
                  color: textColor
                }
              }
            },
            scales: {
              y: {
                beginAtZero: false,
                grid: {
                  color: gridColor
                },
                ticks: {
                  color: textColor,
                  callback: function(value) {
                    return '$' + Math.round(value).toLocaleString()
                  }
                }
              },
              x: {
                grid: {
                  color: gridColor
                },
                ticks: {
                  color: textColor,
                  maxTicksLimit: 8
                }
              }
            }
          }
        }

        console.log('12. Chart config created')

        // 创建图表
        chart = new Chart(ctx, config)
        
        console.log('13. ✅ Chart created successfully:', chart)
        console.log('=== FullBacktest updateChart Debug End ===')

      } catch (error) {
        console.error('❌ Chart creation error:', error)
        equityChartContainer.value.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: #f44336; background: #ffebee; border-radius: 8px;">
            <h4>图表创建失败</h4>
            <p>错误: ${error.message}</p>
            <button onclick="location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
              刷新页面
            </button>
          </div>
        `
      }
    }

    const debugChart = () => {
      console.log('=== FullBacktest Chart Debug Info ===')
      console.log('Chart.js available:', typeof Chart !== 'undefined')
      console.log('Container element:', equityChartContainer.value)
      console.log('Result data:', result.value)
      console.log('Strategies:', result.value?.strategies)
      if (result.value?.strategies) {
        Object.entries(result.value.strategies).forEach(([name, data]) => {
          console.log(`${name} equity curve:`, data.equity_curve?.length)
          console.log(`${name} timestamps:`, data.timestamps?.length)
        })
      }
      console.log('DOM ready:', document.readyState)
      console.log('=====================================')
    }

    const getStrategyName = (strategy) => {
      const names = {
        'long': '做多网格',
        'short': '做空网格',
        'neutral': '中性网格'
      }
      return names[strategy] || strategy
    }

    const formatNumber = (num) => parseFloat(num).toFixed(2)
    const formatPercent = (num) => (num * 100).toFixed(2) + '%'

    return {
      symbol, initialCapital, days, leverage,
      loading, result, message, equityChartContainer,
      runBacktest, getStrategyName, formatNumber, formatPercent, debugChart
    }
  }
}
</script>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1rem;
  margin: 0 1rem 1.5rem 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card h2 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.25rem;
  font-weight: 600;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 500;
  color: #555;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group select,
.form-group input {
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 0.9rem;
  transition: border-color 0.3s ease;
}

.form-group select:focus,
.form-group input:focus {
  outline: none;
  border-color: #007bff;
}

.button-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-primary {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: transform 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.message {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  font-weight: 500;
  opacity: 0;
  transform: translateY(-10px);
  transition: all 0.3s ease;
}

.message.active {
  opacity: 1;
  transform: translateY(0);
}

.message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.comparison-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1.5rem;
  border: 2px solid #e0e0e0;
  transition: border-color 0.3s ease;
}

.comparison-card:hover {
  border-color: #007bff;
}

.comparison-card h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.2rem;
  text-align: center;
  padding: 0.5rem;
  background: white;
  border-radius: 8px;
}

.strategy-stats {
  display: grid;
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.stat-item .label {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
}

.stat-item .value {
  font-weight: 600;
  color: #333;
  font-family: monospace;
}

.positive {
  color: #28a745;
}

.negative {
  color: #dc3545;
}

.chart-container {
  min-height: 400px;
  height: 400px;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}
</style>
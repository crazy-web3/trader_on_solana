<template>
  <div>
    <!-- 查询参数 -->
    <div class="card">
      <h2>⚙️ 查询参数</h2>
      <div class="form-grid">
        <div class="form-group">
          <label>币种</label>
          <select v-model="symbol">
            <option value="ETH/USDT">ETH/USDT - 以太坊</option>
            <option value="BTC/USDT">BTC/USDT - 比特币</option>
            <option value="BNB/USDT">BNB/USDT - 币安币</option>
            <option value="SOL/USDT">SOL/USDT - Solana</option>
          </select>
        </div>
        <div class="form-group">
          <label>时间周期</label>
          <select v-model="interval">
            <option value="4h">4小时</option>
            <option value="1h">1小时</option>
            <option value="1d">1天</option>
            <option value="15m">15分钟</option>
            <option value="5m">5分钟</option>
            <option value="1m">1分钟</option>
          </select>
        </div>
        <div class="form-group">
          <label>时间范围 (天)</label>
          <input v-model.number="days" type="number" min="1" max="365" placeholder="90">
        </div>
      </div>
      <div class="button-group">
        <button class="btn-primary" @click="fetchKlines" :disabled="loading">
          {{ loading ? '加载中...' : '🔍 查询数据' }}
        </button>
        <button class="btn-secondary" @click="downloadCSV" :disabled="!klines.length">
          📥 下载CSV
        </button>
        <button class="btn-secondary" @click="clearCache">🗑️ 清空缓存</button>
      </div>
      <div v-if="message" :class="['message', message.type, 'active']">
        {{ message.text }}
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="card" v-if="stats">
      <h2>📊 数据统计</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">数据条数</div>
          <div class="stat-value">{{ stats.count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最高价</div>
          <div class="stat-value">${{ stats.maxPrice }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最低价</div>
          <div class="stat-value">${{ stats.minPrice }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均价</div>
          <div class="stat-value">${{ stats.avgPrice }}</div>
        </div>
      </div>
    </div>

    <!-- K线图表 -->
    <div class="card">
      <h2>📈 K线图表</h2>
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>正在加载 {{ symbol }} {{ interval }} 数据...</p>
      </div>
      <div v-else-if="klines.length > 0" class="chart-container" ref="chartContainer"></div>
      <div v-else class="empty-chart">
        <p>暂无图表数据</p>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="card" v-if="klines.length > 0">
      <h2>📋 K线数据</h2>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>开盘</th>
              <th>最高</th>
              <th>最低</th>
              <th>收盘</th>
              <th>成交量</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(kline, idx) in klines.slice(0, 50)" :key="idx">
              <td>{{ formatTime(kline.timestamp) }}</td>
              <td>${{ formatNumber(kline.open) }}</td>
              <td>${{ formatNumber(kline.high) }}</td>
              <td>${{ formatNumber(kline.low) }}</td>
              <td>${{ formatNumber(kline.close) }}</td>
              <td>{{ formatNumber(kline.volume) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const symbol = ref('ETH/USDT')
    const interval = ref('4h')
    const days = ref(90)
    const loading = ref(false)
    const klines = ref([])
    const stats = ref(null)
    const message = ref(null)
    const chartContainer = ref(null)
    let chart = null

    const fetchKlines = async () => {
      loading.value = true
      message.value = null

      try {
        const response = await fetch(
          `/api/klines?symbol=${symbol.value}&interval=${interval.value}&days=${days.value}`
        )
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        console.log('API Response:', data)
        
        // Handle both response formats
        const klinesData = data.data || data
        klines.value = Array.isArray(klinesData) ? klinesData : []
        
        if (klines.value.length === 0) {
          message.value = { type: 'error', text: '❌ 没有获取到数据' }
        } else {
          console.log('Loaded klines:', klines.value.length)
          calculateStats()
          // 延迟更新图表，确保DOM已更新
          setTimeout(() => {
            updateChart()
          }, 200)
          message.value = { type: 'success', text: `✅ 成功加载 ${klines.value.length} 条数据` }
        }
      } catch (error) {
        console.error('Fetch error:', error)
        message.value = { type: 'error', text: `❌ 错误: ${error.message}` }
      } finally {
        loading.value = false
      }
    }

    const calculateStats = () => {
      if (klines.value.length === 0) return

      const prices = klines.value.map(k => k.close)
      const maxPrice = Math.max(...klines.value.map(k => k.high))
      const minPrice = Math.min(...klines.value.map(k => k.low))
      const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length

      stats.value = {
        count: klines.value.length,
        maxPrice: maxPrice.toFixed(2),
        minPrice: minPrice.toFixed(2),
        avgPrice: avgPrice.toFixed(2)
      }
    }

    const updateChart = () => {
      if (!chartContainer.value || klines.value.length === 0) return

      const tryCreateChart = (attempt = 1) => {
        try {
          // 清空容器并创建新的图表div
          chartContainer.value.innerHTML = '<div id="tv-chart" style="width: 100%; height: 500px;"></div>'
          
          // 等待DOM更新
          setTimeout(() => {
            const chartDiv = document.getElementById('tv-chart')
            if (!chartDiv) {
              if (attempt < 3) {
                console.log(`Chart creation attempt ${attempt} failed, retrying...`)
                tryCreateChart(attempt + 1)
              }
              return
            }
            
            // Check if LightweightCharts is available
            if (typeof LightweightCharts === 'undefined') {
              console.warn('LightweightCharts not loaded, creating simple chart')
              createSimpleChart(chartDiv)
              return
            }
            
            const tvChart = LightweightCharts.createChart(chartDiv, {
              layout: { 
                textColor: '#333', 
                background: { color: '#ffffff' } 
              },
              grid: {
                vertLines: { color: '#f0f0f0' },
                horzLines: { color: '#f0f0f0' }
              },
              timeScale: { 
                timeVisible: true, 
                secondsVisible: false,
                borderColor: '#e0e0e0'
              },
              rightPriceScale: {
                borderColor: '#e0e0e0'
              },
              width: chartDiv.clientWidth,
              height: 500
            })

            const candlestickSeries = tvChart.addCandlestickSeries({
              upColor: '#10b981',
              downColor: '#ef4444',
              borderUpColor: '#10b981',
              borderDownColor: '#ef4444',
              wickUpColor: '#10b981',
              wickDownColor: '#ef4444'
            })

            // 准备数据并排序
            const candleData = klines.value
              .filter(k => k && k.timestamp && k.open && k.high && k.low && k.close) // 过滤无效数据
              .map(k => ({
                time: Math.floor(k.timestamp / 1000),
                open: parseFloat(k.open),
                high: parseFloat(k.high),
                low: parseFloat(k.low),
                close: parseFloat(k.close)
              }))
              .sort((a, b) => a.time - b.time)

            console.log('Chart data prepared:', candleData.length, 'candles')
            
            if (candleData.length > 0) {
              candlestickSeries.setData(candleData)
              tvChart.timeScale().fitContent()
              
              // 保存图表实例
              chart = tvChart
              
              console.log('Chart created successfully')
            } else {
              console.warn('No valid candle data available')
              createSimpleChart(chartDiv)
            }
            
            // 处理窗口大小变化
            const resizeObserver = new ResizeObserver(() => {
              if (tvChart && chartDiv) {
                tvChart.applyOptions({
                  width: chartDiv.clientWidth,
                  height: 500
                })
              }
            })
            resizeObserver.observe(chartDiv)
            
          }, 100 * attempt) // 增加延迟时间
          
        } catch (error) {
          console.error('Chart error:', error)
          const chartDiv = document.getElementById('tv-chart')
          if (chartDiv) {
            createSimpleChart(chartDiv)
          } else if (attempt < 3) {
            console.log(`Chart creation attempt ${attempt} failed, retrying...`)
            tryCreateChart(attempt + 1)
          }
        }
      }

      tryCreateChart()
    }

    const createSimpleChart = (container) => {
      if (!container || klines.value.length === 0) return
      
      const firstKline = klines.value[0]
      const lastKline = klines.value[klines.value.length - 1]
      const priceChange = lastKline.close - firstKline.open
      const priceChangePercent = ((priceChange / firstKline.open) * 100).toFixed(2)
      const changeColor = priceChange >= 0 ? '#10b981' : '#ef4444'
      const changeIcon = priceChange >= 0 ? '📈' : '📉'
      
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; border: 1px solid #dee2e6;">
          <h3 style="color: #495057; margin-bottom: 1.5rem; font-size: 1.5rem;">${changeIcon} ${symbol.value} K线图表</h3>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
            <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
              <div style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;">数据点数</div>
              <div style="color: #495057; font-size: 1.5rem; font-weight: 600;">${klines.value.length}</div>
            </div>
            
            <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
              <div style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;">当前价格</div>
              <div style="color: #495057; font-size: 1.5rem; font-weight: 600;">$${formatNumber(lastKline?.close)}</div>
            </div>
            
            <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
              <div style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.5rem;">价格变化</div>
              <div style="color: ${changeColor}; font-size: 1.5rem; font-weight: 600;">${priceChangePercent}%</div>
            </div>
          </div>
          
          <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 0.9rem; color: #6c757d;">
            <div>时间范围: ${formatTime(firstKline?.timestamp)} - ${formatTime(lastKline?.timestamp)}</div>
            <div style="margin-top: 0.5rem;">数据周期: ${interval.value} | 总天数: ${days.value}天</div>
          </div>
          
          <div style="margin-top: 1rem; padding: 0.75rem; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; color: #856404; font-size: 0.85rem;">
            💡 提示: 图表库加载中，显示数据概览。如需完整图表，请刷新页面。
          </div>
        </div>
      `
    }

    const clearCache = async () => {
      if (!confirm('确定要清空缓存吗？')) return

      try {
        await fetch('/api/cache/clear', { method: 'POST' })
        message.value = { type: 'success', text: '✅ 缓存已清空' }
      } catch (error) {
        message.value = { type: 'error', text: `❌ 错误: ${error.message}` }
      }
    }

    const downloadCSV = async () => {
      try {
        message.value = { type: 'info', text: '📥 正在准备下载...' }
        
        // 构建下载URL
        const url = `/api/klines/export?symbol=${symbol.value}&interval=${interval.value}&days=${days.value}`
        
        // 创建一个隐藏的a标签来触发下载
        const link = document.createElement('a')
        link.href = url
        link.download = `${symbol.value.replace('/', '_')}_${interval.value}_${days.value}d.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        message.value = { type: 'success', text: '✅ CSV文件下载已开始' }
      } catch (error) {
        console.error('Download error:', error)
        message.value = { type: 'error', text: `❌ 下载失败: ${error.message}` }
      }
    }

    const formatTime = (ms) => {
      return new Date(ms).toLocaleString('zh-CN')
    }

    const formatNumber = (num) => {
      return parseFloat(num).toFixed(2)
    }

    onMounted(() => {
      // 显示自动加载提示
      message.value = { type: 'info', text: '🔄 正在自动加载 ETH/USDT 4小时 K线数据...' }
      
      // 延迟一点时间让用户看到提示
      setTimeout(() => {
        fetchKlines()
      }, 500)
    })

    return {
      symbol,
      interval,
      days,
      loading,
      klines,
      stats,
      message,
      chartContainer,
      fetchKlines,
      clearCache,
      downloadCSV,
      formatTime,
      formatNumber
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

.card:last-child {
  margin-bottom: 1rem;
}

.card h2 {
  margin: 0 0 1.5rem 0;
  color: #333;
  font-size: 1.25rem;
  font-weight: 600;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
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

.btn-secondary {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s ease;
}

.btn-secondary:hover {
  background: #5a6268;
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

.message.info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #333;
}

.chart-container {
  min-height: 500px;
  border-radius: 8px;
  overflow: hidden;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

.empty-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #999;
  background: #f8f9fa;
  border-radius: 8px;
}

.table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  color: #555;
  font-size: 0.9rem;
}

td {
  font-size: 0.9rem;
  color: #333;
}

tr:hover {
  background: #f8f9fa;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .button-group {
    flex-direction: column;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
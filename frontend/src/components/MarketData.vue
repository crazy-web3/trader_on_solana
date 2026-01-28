<template>
  <div>
    <!-- 查询参数 -->
    <div class="card">
      <h2>⚙️ 查询参数</h2>
      <div class="form-grid">
        <div class="form-group">
          <label>币种</label>
          <select v-model="symbol">
            <option value="BTC/USDT">BTC/USDT - 比特币</option>
            <option value="ETH/USDT">ETH/USDT - 以太坊</option>
            <option value="BNB/USDT">BNB/USDT - 币安币</option>
            <option value="SOL/USDT">SOL/USDT - Solana</option>
          </select>
        </div>
        <div class="form-group">
          <label>时间周期</label>
          <select v-model="interval">
            <option value="1m">1分钟</option>
            <option value="5m">5分钟</option>
            <option value="15m">15分钟</option>
            <option value="1h">1小时</option>
            <option value="4h">4小时</option>
            <option value="1d">1天</option>
          </select>
        </div>
        <div class="form-group">
          <label>时间范围 (天)</label>
          <input v-model.number="days" type="number" min="1" max="365">
        </div>
      </div>
      <div class="button-group">
        <button class="btn-primary" @click="fetchKlines" :disabled="loading">
          {{ loading ? '加载中...' : '🔍 查询数据' }}
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
    <div class="card" v-if="klines.length > 0">
      <h2>📈 K线图表</h2>
      <div class="chart-container" ref="chartContainer"></div>
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
    const symbol = ref('BTC/USDT')
    const interval = ref('1h')
    const days = ref(7)
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
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        
        // Handle both response formats
        const klinesData = data.data || data
        klines.value = Array.isArray(klinesData) ? klinesData : (data.data || [])
        
        if (klines.value.length === 0) {
          message.value = { type: 'error', text: '❌ 没有获取到数据' }
        } else {
          calculateStats()
          updateChart()
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

      try {
        chartContainer.value.innerHTML = '<div id="tv-chart" style="width: 100%; height: 400px;"></div>'

        const chartDiv = document.getElementById('tv-chart')
        
        // Check if LightweightCharts is available
        if (typeof LightweightCharts === 'undefined') {
          console.warn('LightweightCharts not loaded, skipping chart')
          return
        }
        
        const tvChart = LightweightCharts.createChart(chartDiv, {
          layout: { textColor: '#cbd5e1', background: { color: '#1e293b' } },
          timeScale: { timeVisible: true, secondsVisible: false }
        })

        const candlestickSeries = tvChart.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderUpColor: '#10b981',
          borderDownColor: '#ef4444'
        })

        const candleData = klines.value.map(k => ({
          time: Math.floor(k.timestamp / 1000),
          open: k.open,
          high: k.high,
          low: k.low,
          close: k.close
        }))

        candlestickSeries.setData(candleData)
        tvChart.timeScale().fitContent()
        chart = tvChart
      } catch (error) {
        console.error('Chart error:', error)
      }
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

    const formatTime = (ms) => {
      return new Date(ms).toLocaleString('zh-CN')
    }

    const formatNumber = (num) => {
      return parseFloat(num).toFixed(2)
    }

    onMounted(() => {
      fetchKlines()
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
      formatTime,
      formatNumber
    }
  }
}
</script>

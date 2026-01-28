<template>
  <div>
    <!-- 参数配置 -->
    <div class="card">
      <h2>⚙️ 完整回测参数</h2>
      <div class="form-grid">
        <div class="form-group">
          <label>币种</label>
          <select v-model="symbol">
            <option value="BTC/USDT">BTC/USDT</option>
            <option value="ETH/USDT">ETH/USDT</option>
            <option value="SOL/USDT">SOL/USDT</option>
          </select>
        </div>
        <div class="form-group">
          <label>策略模式</label>
          <select v-model="mode">
            <option value="long">做多 (Long)</option>
            <option value="short">做空 (Short)</option>
            <option value="neutral">中性 (Neutral)</option>
          </select>
        </div>
        <div class="form-group">
          <label>下限价格</label>
          <input v-model.number="lowerPrice" type="number" step="100">
        </div>
        <div class="form-group">
          <label>上限价格</label>
          <input v-model.number="upperPrice" type="number" step="100">
        </div>
        <div class="form-group">
          <label>网格数量</label>
          <input v-model.number="gridCount" type="number" min="2" max="100">
        </div>
        <div class="form-group">
          <label>初始资金</label>
          <input v-model.number="initialCapital" type="number" step="100">
        </div>
        <div class="form-group">
          <label>开始日期</label>
          <input v-model="startDate" type="date">
        </div>
        <div class="form-group">
          <label>结束日期</label>
          <input v-model="endDate" type="date">
        </div>
      </div>
      <div class="button-group">
        <button class="btn-primary" @click="runBacktest" :disabled="loading">
          {{ loading ? '回测中...' : '🚀 开始回测' }}
        </button>
      </div>
      <div v-if="message" :class="['message', message.type, 'active']">
        {{ message.text }}
      </div>
    </div>

    <!-- 回测结果 -->
    <div class="card" v-if="result">
      <h2>📊 回测结果</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">初始资金</div>
          <div class="stat-value">${{ formatNumber(result.initial_capital) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最终资金</div>
          <div class="stat-value">${{ formatNumber(result.final_capital) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">总收益率</div>
          <div class="stat-value" :class="result.metrics.total_return >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(result.metrics.total_return) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">年化收益</div>
          <div class="stat-value" :class="result.metrics.annual_return >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(result.metrics.annual_return) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最大回撤</div>
          <div class="stat-value negative">{{ formatPercent(result.metrics.max_drawdown) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Sharpe比率</div>
          <div class="stat-value">{{ formatNumber(result.metrics.sharpe_ratio) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">胜率</div>
          <div class="stat-value">{{ formatPercent(result.metrics.win_rate) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">手续费占比</div>
          <div class="stat-value">{{ formatPercent(result.metrics.fee_ratio) }}</div>
        </div>
      </div>
    </div>

    <!-- 权益曲线 -->
    <div class="card" v-if="result && result.equity_curve">
      <h2>📈 权益曲线</h2>
      <div class="chart-container" ref="equityChartContainer"></div>
    </div>

    <!-- 交易记录 -->
    <div class="card" v-if="result && result.trades && result.trades.length > 0">
      <h2>💰 交易记录 (前50条)</h2>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>方向</th>
              <th>价格</th>
              <th>数量</th>
              <th>手续费</th>
              <th>盈亏</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(trade, idx) in result.trades.slice(0, 50)" :key="idx">
              <td>{{ formatTime(trade.timestamp) }}</td>
              <td :class="trade.side === 'buy' ? 'positive' : 'negative'">
                {{ trade.side === 'buy' ? '买入' : '卖出' }}
              </td>
              <td>${{ formatNumber(trade.price) }}</td>
              <td>{{ formatNumber(trade.quantity) }}</td>
              <td>${{ formatNumber(trade.fee) }}</td>
              <td :class="trade.pnl >= 0 ? 'positive' : 'negative'">
                {{ trade.side === 'sell' ? formatNumber(trade.pnl) : '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  setup() {
    const symbol = ref('BTC/USDT')
    const mode = ref('long')
    const lowerPrice = ref(40000)
    const upperPrice = ref(60000)
    const gridCount = ref(10)
    const initialCapital = ref(10000)
    const startDate = ref(new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
    const endDate = ref(new Date().toISOString().split('T')[0])
    const loading = ref(false)
    const result = ref(null)
    const message = ref(null)
    const equityChartContainer = ref(null)
    let chart = null

    const runBacktest = async () => {
      loading.value = true
      message.value = null

      try {
        const response = await fetch('/api/backtest/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: symbol.value,
            mode: mode.value,
            lower_price: lowerPrice.value,
            upper_price: upperPrice.value,
            grid_count: gridCount.value,
            initial_capital: initialCapital.value,
            start_date: startDate.value,
            end_date: endDate.value
          })
        })
        const data = await response.json()
        result.value = data
        updateChart()
        message.value = { type: 'success', text: '✅ 回测完成' }
      } catch (error) {
        message.value = { type: 'error', text: `❌ 错误: ${error.message}` }
      } finally {
        loading.value = false
      }
    }

    const updateChart = () => {
      if (!equityChartContainer.value || !result.value.equity_curve) return

      equityChartContainer.value.innerHTML = '<canvas id="equityChart"></canvas>'
      const ctx = document.getElementById('equityChart').getContext('2d')

      const labels = result.value.timestamps.map(ts => {
        const date = new Date(ts)
        return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit' })
      })

      if (chart) chart.destroy()

      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: '权益曲线',
            data: result.value.equity_curve,
            borderColor: '#60a5fa',
            backgroundColor: 'rgba(96, 165, 250, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: true, position: 'top' } },
          scales: { y: { beginAtZero: false } }
        }
      })
    }

    const formatNumber = (num) => parseFloat(num).toFixed(2)
    const formatPercent = (num) => (num * 100).toFixed(2) + '%'
    const formatTime = (ms) => new Date(ms).toLocaleString('zh-CN')

    return {
      symbol, mode, lowerPrice, upperPrice, gridCount, initialCapital, startDate, endDate,
      loading, result, message, equityChartContainer,
      runBacktest, formatNumber, formatPercent, formatTime
    }
  }
}
</script>

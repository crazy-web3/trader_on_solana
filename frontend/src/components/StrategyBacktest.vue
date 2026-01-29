<template>
  <div>
    <!-- 参数配置 -->
    <div class="card">
      <h2>⚙️ 策略参数</h2>
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
          <label>策略模式</label>
          <select v-model="mode">
            <option value="long">做多 (Long)</option>
            <option value="short">做空 (Short)</option>
            <option value="neutral">中性 (Neutral)</option>
          </select>
        </div>
        <div class="form-group">
          <label>回测天数</label>
          <input v-model.number="days" type="number" min="1" max="365" @change="updatePricePreview">
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="autoCalculateRange" @change="toggleAutoCalculate"> 
            自动计算价格区间
          </label>
        </div>
      </div>
      
      <!-- 价格区间预览 -->
      <div v-if="autoCalculateRange" class="price-preview-section">
        <h3>📊 价格区间预览</h3>
        <div v-if="loadingPreview" class="loading-text">正在计算价格区间...</div>
        <div v-else-if="priceRangePreview" class="price-preview">
          <div class="preview-stats">
            <div class="stat-item">
              <span class="label">当前价格:</span>
              <span class="value">${{ formatNumber(priceRangePreview.current_price) }}</span>
            </div>
            <div class="stat-item">
              <span class="label">历史高点:</span>
              <span class="value">${{ formatNumber(priceRangePreview.historical_high) }}</span>
            </div>
            <div class="stat-item">
              <span class="label">历史低点:</span>
              <span class="value">${{ formatNumber(priceRangePreview.historical_low) }}</span>
            </div>
          </div>
          <div class="calculated-range">
            <div class="range-item">
              <span class="label">计算区间:</span>
              <span class="value">${{ formatNumber(priceRangePreview.calculated_range.lower_price) }} - ${{ formatNumber(priceRangePreview.calculated_range.upper_price) }}</span>
            </div>
            <div class="range-item">
              <span class="label">网格数量:</span>
              <span class="value">{{ priceRangePreview.calculated_range.grid_count }} 个</span>
            </div>
            <div class="range-item">
              <span class="label">网格间距:</span>
              <span class="value">${{ formatNumber(priceRangePreview.calculated_range.grid_spacing) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 手动设置价格区间 -->
      <div v-if="!autoCalculateRange" class="manual-price-section">
        <h3>⚙️ 手动设置价格区间</h3>
        <div class="form-grid">
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
        </div>
      </div>
      
      <div class="form-grid">
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
            <option value="20">20x</option>
          </select>
        </div>
        <div class="form-group">
          <label>资金费率 (%)</label>
          <input v-model.number="fundingRate" type="number" step="0.001" min="-1" max="1" placeholder="0.000">
        </div>
        <div class="form-group">
          <label>资金费率周期 (小时)</label>
          <select v-model.number="fundingInterval">
            <option value="1">1小时</option>
            <option value="4">4小时</option>
            <option value="8">8小时</option>
            <option value="24">24小时</option>
          </select>
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
          <div class="stat-value" :class="result.total_return >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(result.total_return) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">总交易数</div>
          <div class="stat-value">{{ result.total_trades }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">盈利交易</div>
          <div class="stat-value positive">{{ result.winning_trades }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">亏损交易</div>
          <div class="stat-value negative">{{ result.losing_trades }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">胜率</div>
          <div class="stat-value">{{ formatPercent(result.win_rate) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最大回撤</div>
          <div class="stat-value negative">{{ formatPercent(result.max_drawdown_pct) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">交易手续费</div>
          <div class="stat-value">${{ formatNumber(result.total_fees || 0) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">资金费用</div>
          <div class="stat-value" :class="(result.total_funding_fees || 0) > 0 ? 'negative' : 'positive'">
            ${{ formatNumber(result.total_funding_fees || 0) }}
          </div>
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
      <h2>💰 交易记录</h2>
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
            <tr v-for="(trade, idx) in result.trades" :key="idx">
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
import { ref, onMounted } from 'vue'

export default {
  setup() {
    const symbol = ref('ETH/USDT')
    const mode = ref('long')
    const lowerPrice = ref(3200)
    const upperPrice = ref(3600)
    const gridCount = ref(10)
    const initialCapital = ref(10000)
    const days = ref(90)
    const leverage = ref(1.0)
    const fundingRate = ref(0.0)
    const fundingInterval = ref(8)
    const autoCalculateRange = ref(true)
    const priceRangePreview = ref(null)
    const loadingPreview = ref(false)
    const loading = ref(false)
    const result = ref(null)
    const message = ref(null)
    const equityChartContainer = ref(null)
    let chart = null

    const updatePricePreview = async () => {
      if (!autoCalculateRange.value) return
      
      loadingPreview.value = true
      try {
        const response = await fetch('/api/strategy/price-range', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: symbol.value,
            days: days.value
          })
        })
        
        if (response.ok) {
          priceRangePreview.value = await response.json()
        } else {
          console.error('Failed to get price range preview')
        }
      } catch (error) {
        console.error('Price preview error:', error)
      } finally {
        loadingPreview.value = false
      }
    }

    const toggleAutoCalculate = () => {
      if (autoCalculateRange.value) {
        updatePricePreview()
      } else {
        priceRangePreview.value = null
      }
    }

    const runBacktest = async () => {
      loading.value = true
      message.value = null

      try {
        const requestBody = {
          symbol: symbol.value,
          mode: mode.value,
          initial_capital: initialCapital.value,
          days: days.value,
          leverage: leverage.value,
          funding_rate: fundingRate.value / 100, // Convert percentage to decimal
          funding_interval: fundingInterval.value,
          auto_calculate_range: autoCalculateRange.value
        }

        // Add manual parameters if not auto-calculating
        if (!autoCalculateRange.value) {
          requestBody.lower_price = lowerPrice.value
          requestBody.upper_price = upperPrice.value
          requestBody.grid_count = gridCount.value
        }

        const response = await fetch('/api/strategy/backtest', {
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
        
        // Update manual fields with calculated values if auto-calculated
        if (autoCalculateRange.value && data.calculated_params) {
          lowerPrice.value = data.calculated_params.lower_price
          upperPrice.value = data.calculated_params.upper_price
          gridCount.value = data.calculated_params.grid_count
        }
        
        updateChart()
        message.value = { type: 'success', text: '✅ 回测完成' }
      } catch (error) {
        console.error('Backtest error:', error)
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
        return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit' })
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

    // Auto-update price preview when component mounts
    onMounted(() => {
      if (autoCalculateRange.value) {
        updatePricePreview()
      }
    })

    return {
      symbol, mode, lowerPrice, upperPrice, gridCount, initialCapital, days, leverage, fundingRate, fundingInterval,
      autoCalculateRange, priceRangePreview, loadingPreview,
      loading, result, message, equityChartContainer,
      runBacktest, updatePricePreview, toggleAutoCalculate, formatTime, formatNumber, formatPercent
    }
  }
}
</script>
<style scoped>
.price-preview-section, .manual-price-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1rem;
  margin: 1rem 0;
  border: 1px solid #e0e0e0;
}

.price-preview-section h3, .manual-price-section h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
}

.loading-text {
  text-align: center;
  color: #666;
  font-style: italic;
}

.price-preview {
  display: grid;
  gap: 1rem;
}

.preview-stats, .calculated-range {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.stat-item, .range-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.stat-item .label, .range-item .label {
  font-weight: 500;
  color: #666;
  font-size: 0.9rem;
}

.stat-item .value, .range-item .value {
  font-weight: 600;
  color: #333;
  font-family: monospace;
}

.form-group label input[type="checkbox"] {
  margin-right: 0.5rem;
}

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

.stat-value.positive {
  color: #28a745;
}

.stat-value.negative {
  color: #dc3545;
}

.chart-container {
  min-height: 400px;
  border-radius: 8px;
  overflow: hidden;
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

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .preview-stats, .calculated-range {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
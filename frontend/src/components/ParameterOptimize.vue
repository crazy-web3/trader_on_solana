<template>
  <div>
    <!-- 参数配置 -->
    <div class="card">
      <h2>⚙️ Grid Search 参数优化</h2>
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
        <div class="form-group">
          <label>优化指标</label>
          <select v-model="metric">
            <option value="total_return">总收益率</option>
            <option value="annual_return">年化收益</option>
            <option value="sharpe_ratio">Sharpe比率</option>
            <option value="win_rate">胜率</option>
          </select>
        </div>
      </div>

      <h3 style="margin-top: 20px; margin-bottom: 15px; color: #f1f5f9;">参数范围</h3>
      <div class="form-grid">
        <div class="form-group">
          <label>网格数量范围</label>
          <input v-model="gridCountRange" type="text" placeholder="例: 5,10,15,20">
        </div>
        <div class="form-group">
          <label>下限价格范围</label>
          <input v-model="lowerPriceRange" type="text" placeholder="例: 38000,40000,42000">
        </div>
        <div class="form-group">
          <label>上限价格范围</label>
          <input v-model="upperPriceRange" type="text" placeholder="例: 58000,60000,62000">
        </div>
      </div>

      <div class="button-group">
        <button class="btn-primary" @click="runOptimize" :disabled="loading">
          {{ loading ? '优化中...' : '⚡ 开始优化' }}
        </button>
      </div>
      <div v-if="message" :class="['message', message.type, 'active']">
        {{ message.text }}
      </div>
    </div>

    <!-- 最优结果 -->
    <div class="card" v-if="result">
      <h2>🏆 最优结果</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">网格数量</div>
          <div class="stat-value">{{ result.best_params.grid_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">下限价格</div>
          <div class="stat-value">${{ result.best_params.lower_price }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">上限价格</div>
          <div class="stat-value">${{ result.best_params.upper_price }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">总收益率</div>
          <div class="stat-value positive">
            {{ formatPercent(result.best_result.metrics.total_return) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">年化收益</div>
          <div class="stat-value positive">
            {{ formatPercent(result.best_result.metrics.annual_return) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最大回撤</div>
          <div class="stat-value negative">
            {{ formatPercent(result.best_result.metrics.max_drawdown) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Sharpe比率</div>
          <div class="stat-value">{{ formatNumber(result.best_result.metrics.sharpe_ratio) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">胜率</div>
          <div class="stat-value">{{ formatPercent(result.best_result.metrics.win_rate) }}</div>
        </div>
      </div>
    </div>

    <!-- 所有结果对比 -->
    <div class="card" v-if="result && result.all_results">
      <h2>📊 所有结果对比 (前20个)</h2>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>网格数</th>
              <th>下限价</th>
              <th>上限价</th>
              <th>总收益率</th>
              <th>年化收益</th>
              <th>最大回撤</th>
              <th>Sharpe</th>
              <th>胜率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(res, idx) in result.all_results.slice(0, 20)" :key="idx">
              <td>{{ idx + 1 }}</td>
              <td>{{ res.config.grid_count }}</td>
              <td>${{ res.config.lower_price }}</td>
              <td>${{ res.config.upper_price }}</td>
              <td :class="res.metrics.total_return >= 0 ? 'positive' : 'negative'">
                {{ formatPercent(res.metrics.total_return) }}
              </td>
              <td :class="res.metrics.annual_return >= 0 ? 'positive' : 'negative'">
                {{ formatPercent(res.metrics.annual_return) }}
              </td>
              <td class="negative">{{ formatPercent(res.metrics.max_drawdown) }}</td>
              <td>{{ formatNumber(res.metrics.sharpe_ratio) }}</td>
              <td>{{ formatPercent(res.metrics.win_rate) }}</td>
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
    const initialCapital = ref(10000)
    const startDate = ref(new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0])
    const endDate = ref(new Date().toISOString().split('T')[0])
    const metric = ref('total_return')
    const gridCountRange = ref('5,10,15,20')
    const lowerPriceRange = ref('38000,40000,42000')
    const upperPriceRange = ref('58000,60000,62000')
    const loading = ref(false)
    const result = ref(null)
    const message = ref(null)

    const parseRange = (str) => {
      return str.split(',').map(s => {
        const num = parseFloat(s.trim())
        return isNaN(num) ? null : num
      }).filter(n => n !== null)
    }

    const runOptimize = async () => {
      loading.value = true
      message.value = null

      try {
        const gridCounts = parseRange(gridCountRange.value)
        const lowerPrices = parseRange(lowerPriceRange.value)
        const upperPrices = parseRange(upperPriceRange.value)

        if (gridCounts.length === 0 || lowerPrices.length === 0 || upperPrices.length === 0) {
          message.value = { type: 'error', text: '❌ 参数范围格式错误' }
          loading.value = false
          return
        }

        const response = await fetch('/api/backtest/grid-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: symbol.value,
            mode: mode.value,
            lower_price: lowerPrices[0],
            upper_price: upperPrices[0],
            grid_count: gridCounts[0],
            initial_capital: initialCapital.value,
            start_date: startDate.value,
            end_date: endDate.value,
            parameter_ranges: {
              grid_count: gridCounts,
              lower_price: lowerPrices,
              upper_price: upperPrices
            },
            metric: metric.value
          })
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || '优化失败')
        }
        
        const data = await response.json()
        result.value = data
        message.value = { type: 'success', text: `✅ 优化完成，共测试 ${data.all_results.length} 个组合` }
      } catch (error) {
        console.error('Optimize error:', error)
        message.value = { type: 'error', text: `❌ 错误: ${error.message}` }
      } finally {
        loading.value = false
      }
    }

    const formatNumber = (num) => parseFloat(num).toFixed(2)
    const formatPercent = (num) => (num * 100).toFixed(2) + '%'

    return {
      symbol, mode, initialCapital, startDate, endDate, metric,
      gridCountRange, lowerPriceRange, upperPriceRange,
      loading, result, message,
      runOptimize, formatNumber, formatPercent
    }
  }
}
</script>

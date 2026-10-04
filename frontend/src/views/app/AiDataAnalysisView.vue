<template>
  <div class="ai-analysis">
    <header class="ai-analysis__intro">
      <p class="ai-analysis__eyebrow">智能数据中心</p>
      <h1>AI 分析</h1>
      <p>统一承载业务数据洞察、异常识别、趋势预测与历史数据学习能力。</p>
    </header>

    <div class="ai-analysis__grid">
      <section class="feature-card" aria-labelledby="analysis-title">
        <span class="feature-card__index">01</span>
        <div>
          <h2 id="analysis-title">分析洞察</h2>
          <p>面向车辆、燃油、维修和用车台账，提供智能统计、异常检测与可视化洞察。</p>
        </div>
      </section>

      <section class="feature-card" aria-labelledby="learning-title">
        <span class="feature-card__index">02</span>
        <div>
          <h2 id="learning-title">数据学习</h2>
          <p>基于历史业务数据形成预测、推荐和持续学习能力，为后续模型与推理服务提供统一入口。</p>
        </div>
      </section>
    </div>

    <p class="ai-analysis__status">功能接口正在规划中，当前页面用于统一承载后续 AI 能力。</p>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.ai-analysis {
  width: min(100%, 920px);
  margin: 0 auto;
}

.ai-analysis__intro {
  margin-bottom: 1.25rem;
}

.ai-analysis__eyebrow {
  margin: 0 0 0.35rem;
  color: var(--cl-terracotta, #c96442);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.ai-analysis__intro h1 {
  margin: 0 0 0.5rem;
  color: var(--cl-charcoal, #2c2b28);
  font-size: clamp(1.35rem, 3vw, 1.8rem);
}

.ai-analysis__intro > p:last-child,
.feature-card p,
.ai-analysis__status {
  color: var(--cl-olive, #6b6558);
  line-height: 1.65;
}

.ai-analysis__intro > p:last-child {
  max-width: 42rem;
  margin: 0;
  font-size: 0.875rem;
}

.ai-analysis__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.feature-card {
  display: flex;
  min-width: 0;
  gap: 0.85rem;
  padding: 1.15rem;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  border-radius: 16px;
  background: rgba(253, 252, 247, 0.92);
  box-shadow: 0 5px 20px rgba(35, 32, 27, 0.05);
}

.feature-card__index {
  display: inline-grid;
  flex: 0 0 2rem;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 9px;
  background: rgba(201, 100, 66, 0.12);
  color: var(--cl-terracotta, #c96442);
  font-size: 0.75rem;
  font-weight: 700;
}

.feature-card h2 {
  margin: 0 0 0.45rem;
  color: var(--cl-charcoal, #2c2b28);
  font-size: 1rem;
}

.feature-card p {
  margin: 0;
  font-size: 0.8125rem;
}

.ai-analysis__status {
  margin: 1rem 0 0;
  padding: 0.75rem 0.9rem;
  border-radius: 12px;
  background: rgba(142, 132, 109, 0.08);
  font-size: 0.8125rem;
}

@media (max-width: 640px) {
  .ai-analysis__intro h1 {
    display: none;
  }

  .ai-analysis__intro {
    margin-bottom: 0.85rem;
  }

  .ai-analysis__grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.75rem;
  }

  .feature-card {
    padding: 1rem;
  }
}
</style>

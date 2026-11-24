# ECharts 图表配置参考

## 目录

1. [柱状图配置](#柱状图配置)
2. [饼图配置](#饼图配置)
3. [折线图配置](#折线图配置)
4. [仪表盘配置](#仪表盘配置)
5. [雷达图配置](#雷达图配置)

---

## 柱状图配置

### 基础柱状图

```javascript
function initBarChart(containerId, data, title) {
    const chartDom = document.getElementById(containerId);
    if (!chartDom || chartDom.offsetWidth === 0) return;
    
    const myChart = echarts.init(chartDom);
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: data.categories,
            axisLabel: { 
                color: '#94a3b8',
                fontSize: 12
            },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#94a3b8' },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
        },
        series: [{
            data: data.values.map((value, index) => ({
                value: value,
                itemStyle: { 
                    color: data.colors[index] || '#60a5fa',
                    borderRadius: [8, 8, 0, 0]
                }
            })),
            type: 'bar',
            barWidth: '50%',
            label: {
                show: true,
                position: 'top',
                color: '#fff',
                fontWeight: 'bold'
            }
        }]
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}
```

### 排名对比柱状图

```javascript
const rankChartOption = {
    backgroundColor: 'transparent',
    tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
    },
    grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true
    },
    xAxis: {
        type: 'category',
        data: ['GPT-4', 'Claude 3.5', 'Gemini Pro', 'MiMo-V2-Pro', 'Grok', 'Llama 3'],
        axisLabel: { 
            color: '#94a3b8',
            fontSize: 12,
            rotate: 15
        },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
    },
    yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [{
        data: [
            { value: 95, itemStyle: { color: '#60a5fa' } },
            { value: 93, itemStyle: { color: '#60a5fa' } },
            { value: 91, itemStyle: { color: '#60a5fa' } },
            { value: 89, itemStyle: { color: '#f093fb', borderRadius: [8, 8, 0, 0] } },
            { value: 87, itemStyle: { color: '#94a3b8' } },
            { value: 85, itemStyle: { color: '#94a3b8' } }
        ],
        type: 'bar',
        barWidth: '50%',
        label: {
            show: true,
            position: 'top',
            color: '#fff',
            fontWeight: 'bold'
        }
    }]
};
```

---

## 饼图配置

### 环形饼图

```javascript
function initPieChart(containerId, data, title) {
    const chartDom = document.getElementById(containerId);
    if (!chartDom || chartDom.offsetWidth === 0) return;
    
    const myChart = echarts.init(chartDom);
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item'
        },
        legend: {
            bottom: '5%',
            left: 'center',
            textStyle: { color: '#94a3b8' }
        },
        series: [{
            name: title || '数据',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#000',
                borderWidth: 2
            },
            label: {
                show: true,
                position: 'outside',
                color: '#fff',
                formatter: '{b}\n{d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            labelLine: {
                show: true,
                lineStyle: { color: 'rgba(255,255,255,0.3)' }
            },
            data: data
        }]
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}
```

### 价格对比饼图

```javascript
const priceChartOption = {
    backgroundColor: 'transparent',
    tooltip: {
        trigger: 'item'
    },
    legend: {
        bottom: '5%',
        left: 'center',
        textStyle: { color: '#94a3b8' }
    },
    series: [{
        name: 'API价格占比',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
            borderRadius: 10,
            borderColor: '#000',
            borderWidth: 2
        },
        label: {
            show: true,
            position: 'outside',
            color: '#fff',
            formatter: '{b}\n{d}%'
        },
        emphasis: {
            label: {
                show: true,
                fontSize: 16,
                fontWeight: 'bold'
            }
        },
        labelLine: {
            show: true,
            lineStyle: { color: 'rgba(255,255,255,0.3)' }
        },
        data: [
            { value: 83.3, name: 'Claude Opus 4.6', itemStyle: { color: '#94a3b8' } },
            { value: 16.7, name: 'MiMo-V2-Pro', itemStyle: { color: '#fbbf24' } }
        ]
    }]
};
```

---

## 折线图配置

```javascript
function initLineChart(containerId, data, title) {
    const chartDom = document.getElementById(containerId);
    if (!chartDom || chartDom.offsetWidth === 0) return;
    
    const myChart = echarts.init(chartDom);
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: data.series.map(s => s.name),
            textStyle: { color: '#94a3b8' },
            bottom: '5%'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: data.categories,
            axisLabel: { color: '#94a3b8' },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
        },
        yAxis: {
            type: 'value',
            axisLabel: { color: '#94a3b8' },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
        },
        series: data.series.map(s => ({
            name: s.name,
            type: 'line',
            smooth: true,
            data: s.data,
            lineStyle: { width: 3 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: s.color + '40' },
                    { offset: 1, color: s.color + '00' }
                ])
            }
        }))
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}
```

---

## 仪表盘配置

```javascript
function initGaugeChart(containerId, value, title) {
    const chartDom = document.getElementById(containerId);
    if (!chartDom || chartDom.offsetWidth === 0) return;
    
    const myChart = echarts.init(chartDom);
    const option = {
        backgroundColor: 'transparent',
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            splitNumber: 5,
            axisLine: {
                lineStyle: {
                    width: 20,
                    color: [
                        [0.3, '#f87171'],
                        [0.7, '#fbbf24'],
                        [1, '#34d399']
                    ]
                }
            },
            pointer: {
                itemStyle: { color: '#60a5fa' }
            },
            axisTick: {
                distance: -20,
                length: 5,
                lineStyle: { color: '#fff', width: 1 }
            },
            splitLine: {
                distance: -25,
                length: 10,
                lineStyle: { color: '#fff', width: 2 }
            },
            axisLabel: {
                color: '#94a3b8',
                distance: 30,
                fontSize: 12
            },
            detail: {
                valueAnimation: true,
                formatter: '{value}%',
                color: '#fff',
                fontSize: 24,
                offsetCenter: [0, '70%']
            },
            data: [{ value: value, name: title || '' }]
        }]
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}
```

---

## 雷达图配置

```javascript
function initRadarChart(containerId, data, title) {
    const chartDom = document.getElementById(containerId);
    if (!chartDom || chartDom.offsetWidth === 0) return;
    
    const myChart = echarts.init(chartDom);
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item'
        },
        legend: {
            data: data.series.map(s => s.name),
            textStyle: { color: '#94a3b8' },
            bottom: '5%'
        },
        radar: {
            indicator: data.indicators,
            axisName: {
                color: '#94a3b8'
            },
            splitLine: {
                lineStyle: { color: 'rgba(255,255,255,0.1)' }
            },
            splitArea: {
                areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.05)'] }
            },
            axisLine: {
                lineStyle: { color: 'rgba(255,255,255,0.1)' }
            }
        },
        series: [{
            type: 'radar',
            data: data.series.map(s => ({
                name: s.name,
                value: s.value,
                areaStyle: {
                    color: s.color + '40'
                },
                lineStyle: {
                    color: s.color,
                    width: 2
                }
            }))
        }]
    };
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}
```

---

## 颜色参考

```javascript
const COLORS = {
    primary: '#60a5fa',     // 蓝色
    secondary: '#a78bfa',   // 紫色
    accent: '#f093fb',      // 粉色
    success: '#34d399',     // 绿色
    warning: '#fbbf24',     // 黄色
    danger: '#f87171',      // 红色
    gray: '#94a3b8',        // 灰色
    cyan: '#22d3ee',        // 青色
    orange: '#fb923c'       // 橙色
};
```

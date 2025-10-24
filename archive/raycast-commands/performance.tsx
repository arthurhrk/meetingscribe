import { Action, ActionPanel, Detail, Icon, List, showToast, Toast, getPreferenceValues } from "@raycast/api";
import { useEffect, useState } from "react";
import { execSync } from "child_process";

interface SystemStatus {
  status: string;
  health: string;
  cpu: string;
  memory: string;
  transcriptions: number;
  cache_hits: string;
  timestamp: string;
  icon: string;
  color: string;
}

interface DashboardData {
  status: string;
  timestamp: string;
  data: {
    overview: {
      system_health: string;
      transcriptions_today: number;
      cache_hit_rate: string;
      avg_processing_time: string;
      memory_efficiency: string;
    };
    system: {
      cpu_usage: string;
      memory_usage: string;
      status: string;
      peak_cpu: string;
      peak_memory: string;
    };
    transcription: {
      success_rate: string;
      total_today: number;
      avg_time: string;
      cache_hits: number;
      status: string;
    };
    cache: {
      size: string;
      hit_rate: string;
      total_hits: number;
      status: string;
    };
  };
}

function executePerformanceCommand(command: string): any {
  try {
    const result = execSync(`cd "C:\\Users\\arthur.andrade\\OneDrive - Accenture\\Documents\\GitHub\\meetingscribe" && python main.py --performance ${command}`, {
      encoding: 'utf8',
      timeout: 10000
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Performance command failed:', error);
    throw new Error(`Failed to execute performance command: ${error}`);
  }
}

function formatHealthIcon(health: string): string {
  switch (health) {
    case 'optimal': return '✅';
    case 'warning': return '⚠️';
    case 'critical': return '🔴';
    default: return '❓';
  }
}

function formatHealthColor(health: string): string {
  switch (health) {
    case 'optimal': return '#22c55e';
    case 'warning': return '#f59e0b';
    case 'critical': return '#ef4444';
    default: return '#6b7280';
  }
}

interface Preferences { pythonPath: string; projectPath: string; defaultModel: string }

function runPerformance(command: string): any {
  try {
    const { pythonPath, projectPath } = getPreferenceValues<Preferences>();
    const result = execSync(`${pythonPath} main.py --performance ${command}`, {
      cwd: projectPath,
      encoding: 'utf8',
      timeout: 10000,
      windowsHide: true,
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Performance command failed:', error);
    throw new Error(`Failed to execute performance command: ${error}`);
  }
}

export default function PerformanceDashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = runPerformance('dashboard');
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
      setDashboardData(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data');
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Failed to load performance data"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (isLoading) {
    return <Detail isLoading={true} markdown="Loading performance dashboard..." />;
  }

  if (error || !dashboardData) {
    return (
      <Detail
        markdown={`# ❌ Error Loading Dashboard\n\n${error || 'Unknown error occurred'}`}
        actions={
          <ActionPanel>
            <Action title="Retry" onAction={loadDashboardData} icon={Icon.RotateClockwise} />
          </ActionPanel>
        }
      />
    );
  }

  const { data } = dashboardData;
  const healthIcon = formatHealthIcon(data.overview.system_health);
  const healthColor = formatHealthColor(data.overview.system_health);

  const markdownContent = `
# ${healthIcon} MeetingScribe Performance Dashboard

## 📊 System Overview
- **Health Status**: ${data.overview.system_health.toUpperCase()}
- **Transcriptions Today**: ${data.overview.transcriptions_today}
- **Cache Hit Rate**: ${data.overview.cache_hit_rate}
- **Average Processing Time**: ${data.overview.avg_processing_time}
- **Memory Efficiency**: ${data.overview.memory_efficiency}

---

## 🖥️ System Resources
- **CPU Usage**: ${data.system.cpu_usage} (Peak: ${data.system.peak_cpu})
- **Memory Usage**: ${data.system.memory_usage} (Peak: ${data.system.peak_memory})
- **Status**: ${data.system.status}

---

## 📝 Transcription Performance
- **Success Rate**: ${data.transcription.success_rate}
- **Total Today**: ${data.transcription.total_today}
- **Average Time**: ${data.transcription.avg_time}
- **Cache Hits**: ${data.transcription.cache_hits}
- **Status**: ${data.transcription.status}

---

## 💾 Cache Performance
- **Current Size**: ${data.cache.size}
- **Hit Rate**: ${data.cache.hit_rate}
- **Total Hits**: ${data.cache.total_hits}
- **Status**: ${data.cache.status}

---

*Last updated: ${new Date(dashboardData.timestamp).toLocaleString()}*
  `;

  return (
    <Detail
      markdown={markdownContent}
      actions={
        <ActionPanel>
          <Action title="Refresh" onAction={loadDashboardData} icon={Icon.RotateClockwise} />
          <Action.Push 
            title="Quick Status" 
            target={<QuickStatus />} 
            icon={Icon.Gauge} 
          />
          <Action.Push 
            title="Detailed Metrics" 
            target={<DetailedMetrics />} 
            icon={Icon.BarChart} 
          />
          <Action.Push 
            title="Cache Status" 
            target={<CacheStatus />} 
            icon={Icon.HardDrive} 
          />
        </ActionPanel>
      }
    />
  );
}

function QuickStatus() {
  const [statusData, setStatusData] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const data = executePerformanceCommand('status');
        setStatusData(data);
      } catch (err) {
        console.error('Failed to load status:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadStatus();
  }, []);

  if (isLoading || !statusData) {
    return <Detail isLoading={true} markdown="Loading system status..." />;
  }

  const markdown = `
# ${statusData.icon} System Status

- **Health**: ${statusData.health}
- **CPU**: ${statusData.cpu}
- **Memory**: ${statusData.memory}
- **Transcriptions Today**: ${statusData.transcriptions}
- **Cache Efficiency**: ${statusData.cache_hits}

*Updated: ${new Date(statusData.timestamp).toLocaleString()}*
  `;

  return <Detail markdown={markdown} />;
}

function DetailedMetrics() {
  const [metricsData, setMetricsData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const data = executePerformanceCommand('metrics');
        setMetricsData(data);
      } catch (err) {
        console.error('Failed to load metrics:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadMetrics();
  }, []);

  if (isLoading || !metricsData) {
    return <Detail isLoading={true} markdown="Loading detailed metrics..." />;
  }

  const { data } = metricsData;

  const markdown = `
# 📊 Detailed Transcription Metrics

## Performance Summary
- **Total Today**: ${data.today_total}
- **Success Rate**: ${data.success_rate}
- **Average Processing Time**: ${data.average_time}
- **Cache Efficiency**: ${data.cache_efficiency}
- **Status**: ${data.status}

## Recent Transcriptions
${data.recent_transcriptions?.map((t: any, i: number) => `
${i + 1}. **Duration**: ${t.duration} | **Processing**: ${t.processing_time} | **Model**: ${t.model} | **Success**: ${t.success ? '✅' : '❌'}
`).join('') || 'No recent transcriptions'}
  `;

  return <Detail markdown={markdown} />;
}

function CacheStatus() {
  const [cacheData, setCacheData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCache = async () => {
      try {
        const data = executePerformanceCommand('cache');
        setCacheData(data);
      } catch (err) {
        console.error('Failed to load cache status:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadCache();
  }, []);

  if (isLoading || !cacheData) {
    return <Detail isLoading={true} markdown="Loading cache status..." />;
  }

  const { data } = cacheData;

  const markdown = `
# 💾 Cache Performance Status

- **Current Size**: ${data.current_size.toFixed(1)} MB
- **Hit Rate**: ${data.hit_rate}
- **Total Hits**: ${data.total_hits}
- **Efficiency**: ${data.efficiency}
- **Status**: ${data.status}

## Cache Efficiency Analysis
${data.efficiency === 'Excellent' ? '🟢 Cache is performing excellently!' :
  data.efficiency === 'Good' ? '🟡 Cache performance is good' :
  data.efficiency === 'Fair' ? '🟠 Cache could be improved' :
  '🔴 Cache performance needs attention'}
  `;

  return <Detail markdown={markdown} />;
}

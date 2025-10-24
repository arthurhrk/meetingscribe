import { Action, ActionPanel, Detail, Icon, List, showToast, Toast, Form, confirmAlert, Alert, getPreferenceValues } from "@raycast/api";
import { useEffect, useState } from "react";
import { execSync } from "child_process";

interface CacheStatus {
  status: string;
  data: {
    overview: {
      status_text: string;
      status_icon: string;
      status_color: string;
      hit_rate: string;
      memory_usage: string;
      total_entries: number;
    };
    file_cache: {
      entries: number;
      memory_mb: number;
      memory_limit_mb: number;
      memory_usage_percent: number;
      hit_rate: number;
      hits: number;
      misses: number;
      evictions: number;
    };
    audio_cache: {
      entries: number;
      memory_mb: number;
      hit_rate: number;
      compressions: number;
      decompressions: number;
    };
    io_stats: {
      disk_reads: number;
      disk_writes: number;
      compression_ratio: number;
    };
  };
}

interface CacheInsight {
  type: string;
  severity: string;
  title: string;
  description: string;
  suggestion: string;
  icon: string;
}

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

function runCacheCommand(command: string, args?: string): any {
  try {
    const { pythonPath, projectPath } = getPreferenceValues<Preferences>();
    const argsStr = args ? ` ${args}` : '';
    const result = execSync(`${pythonPath} main.py --cache ${command}${argsStr}`, {
      cwd: projectPath,
      encoding: 'utf8',
      timeout: 15000,
      windowsHide: true,
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Cache command failed:', error);
    throw new Error(`Failed to execute cache command: ${error}`);
  }
}

function executeCacheCommand(command: string, args?: string): any {
  try {
    const argsStr = args ? ` ${args}` : '';
    const result = execSync(`cd "C:\\Users\\arthur.andrade\\OneDrive - Accenture\\Documents\\GitHub\\meetingscribe" && python main.py --cache ${command}${argsStr}`, {
      encoding: 'utf8',
      timeout: 15000
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Cache command failed:', error);
    throw new Error(`Failed to execute cache command: ${error}`);
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

export default function CacheManagement() {
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCacheStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = runCacheCommand('status');
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
      setCacheStatus(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cache status');
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Failed to load cache status"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const optimizeCache = async () => {
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Optimizing cache..."
      });

      const result = runCacheCommand('optimize');
      
      if (result.status === 'success') {
        await showToast({
          style: Toast.Style.Success,
          title: "Cache Optimized",
          message: result.data.message
        });
        await loadCacheStatus(); // Refresh data
      } else {
        throw new Error(result.message || 'Optimization failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Optimization Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    }
  };

  const clearCache = async () => {
    const confirmed = await confirmAlert({
      title: "Clear Cache",
      message: "Are you sure you want to clear the entire cache? This action cannot be undone.",
      primaryAction: {
        title: "Clear Cache",
        style: Alert.ActionStyle.Destructive,
      },
    });

    if (confirmed) {
      try {
        await showToast({
          style: Toast.Style.Animated,
          title: "Clearing cache..."
        });

        const result = runCacheCommand('clear');
        
        if (result.status === 'success') {
          await showToast({
            style: Toast.Style.Success,
            title: "Cache Cleared",
            message: result.data.message
          });
          await loadCacheStatus(); // Refresh data
        } else {
          throw new Error(result.message || 'Clear failed');
        }
      } catch (err) {
        await showToast({
          style: Toast.Style.Failure,
          title: "Clear Failed",
          message: err instanceof Error ? err.message : 'Unknown error'
        });
      }
    }
  };

  useEffect(() => {
    loadCacheStatus();
  }, []);

  if (isLoading) {
    return <Detail isLoading={true} markdown="Loading cache status..." />;
  }

  if (error || !cacheStatus) {
    return (
      <Detail
        markdown={`# ❌ Error Loading Cache Status\n\n${error || 'Unknown error occurred'}`}
        actions={
          <ActionPanel>
            <Action title="Retry" onAction={loadCacheStatus} icon={Icon.RotateClockwise} />
          </ActionPanel>
        }
      />
    );
  }

  const { data } = cacheStatus;
  const { overview, file_cache, audio_cache, io_stats } = data;

  const markdownContent = `
# ${overview.status_icon} File Cache Management

## 📊 Cache Overview
- **Status**: ${overview.status_text}
- **Hit Rate**: ${overview.hit_rate}
- **Memory Usage**: ${overview.memory_usage}
- **Total Entries**: ${overview.total_entries}

---

## 📁 File Cache Details
- **Entries**: ${file_cache.entries}
- **Memory**: ${file_cache.memory_mb.toFixed(1)} MB / ${file_cache.memory_limit_mb} MB (${formatPercentage(file_cache.memory_usage_percent)})
- **Hit Rate**: ${formatPercentage(file_cache.hit_rate)}
- **Cache Hits**: ${file_cache.hits.toLocaleString()}
- **Cache Misses**: ${file_cache.misses.toLocaleString()}
- **Evictions**: ${file_cache.evictions.toLocaleString()}

---

## 🎵 Audio Cache Details
- **Entries**: ${audio_cache.entries}
- **Memory**: ${audio_cache.memory_mb.toFixed(1)} MB
- **Hit Rate**: ${formatPercentage(audio_cache.hit_rate)}
- **Compressions**: ${audio_cache.compressions.toLocaleString()}
- **Decompressions**: ${audio_cache.decompressions.toLocaleString()}

---

## 💾 I/O Statistics
- **Disk Reads**: ${io_stats.disk_reads.toLocaleString()}
- **Disk Writes**: ${io_stats.disk_writes.toLocaleString()}
- **Avg Compression**: ${(io_stats.compression_ratio * 100).toFixed(1)}%

---

*Last updated: ${new Date().toLocaleString()}*
  `;

  return (
    <Detail
      markdown={markdownContent}
      actions={
        <ActionPanel>
          <Action title="Refresh" onAction={loadCacheStatus} icon={Icon.RotateClockwise} />
          <Action 
            title="Optimize Cache" 
            onAction={optimizeCache} 
            icon={Icon.Gear}
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          <Action.Push 
            title="Cache Insights" 
            target={<CacheInsights />} 
            icon={Icon.LightBulb} 
          />
          <Action.Push 
            title="Preload Directory" 
            target={<PreloadDirectory />} 
            icon={Icon.Download} 
          />
          <Action 
            title="Clear Cache" 
            onAction={clearCache} 
            icon={Icon.Trash}
            style={Action.Style.Destructive}
            shortcut={{ modifiers: ["cmd", "shift"], key: "delete" }}
          />
          <Action.Push 
            title="Cache Configuration" 
            target={<CacheConfiguration />} 
            icon={Icon.Cog} 
          />
        </ActionPanel>
      }
    />
  );
}

function CacheInsights() {
  const [insights, setInsights] = useState<{ insights: CacheInsight[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        const data = executeCacheCommand('insights');
        setInsights(data.data);
      } catch (err) {
        console.error('Failed to load cache insights:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadInsights();
  }, []);

  if (isLoading || !insights) {
    return <Detail isLoading={true} markdown="Loading cache insights..." />;
  }

  const markdown = `
# 💡 Cache Performance Insights

${insights.insights?.length > 0 ?
  insights.insights.map((insight, i) => `
## ${insight.icon} ${insight.title}

**Type**: ${insight.type} | **Severity**: ${insight.severity.toUpperCase()}

${insight.description}

**💡 Suggestion**: ${insight.suggestion}

---
`).join('') :
  '✅ No specific insights available. Cache is performing well!'
}
  `;

  return <Detail markdown={markdown} />;
}

function PreloadDirectory() {
  const [isLoading, setIsLoading] = useState(false);

  const handlePreload = async (values: { directory: string }) => {
    if (!values.directory.trim()) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Please enter a directory path"
      });
      return;
    }

    setIsLoading(true);
    
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Preloading directory..."
      });

      const result = executeCacheCommand('preload', `--cache-directory "${values.directory}"`);
      
      if (result.status === 'success') {
        await showToast({
          style: Toast.Style.Success,
          title: "Preload Complete",
          message: result.data.message
        });
      } else {
        throw new Error(result.message || 'Preload failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Preload Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm 
            title="Preload Directory" 
            onSubmit={handlePreload}
            icon={Icon.Download}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="directory"
        title="Directory Path"
        placeholder="Enter directory path to preload..."
        info="Preloads audio files and metadata from the specified directory into cache for faster access"
      />
    </Form>
  );
}

function CacheConfiguration() {
  const [config, setConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const data = executeCacheCommand('config');
        setConfig(data.data);
      } catch (err) {
        console.error('Failed to load cache config:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  if (isLoading || !config) {
    return <Detail isLoading={true} markdown="Loading cache configuration..." />;
  }

  const markdown = `
# ⚙️ Cache Configuration

## Current Settings
- **Strategy**: ${config.strategy || 'Unknown'}
- **Compression Level**: ${config.compression_level || 0}
- **TTL Hours**: ${config.ttl_hours || 0}
- **Max Entries**: ${config.max_entries || 0}
- **Memory Limit**: ${config.memory_limit_mb || 0} MB
- **Auto Cleanup**: ${config.auto_cleanup_enabled ? 'Enabled' : 'Disabled'}
- **Persistence**: ${config.persistence_enabled ? 'Enabled' : 'Disabled'}

## Strategy Explanation
- **LRU**: Least Recently Used - removes oldest accessed items
- **LFU**: Least Frequently Used - removes least accessed items  
- **TTL**: Time To Live - removes items after expiration
- **SIZE_BASED**: Removes largest items first
- **INTELLIGENT**: Combines multiple factors for optimal eviction

## Compression Levels
- **0**: No compression (fastest)
- **1**: Fast compression
- **6**: Balanced compression (default)
- **9**: Maximum compression (slowest)
  `;

  return <Detail markdown={markdown} />;
}

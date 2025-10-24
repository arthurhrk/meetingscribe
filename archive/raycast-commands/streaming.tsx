import { Action, ActionPanel, Detail, Icon, List, showToast, Toast, Form, Alert, confirmAlert } from "@raycast/api";
import { useEffect, useState } from "react";
import { execSync } from "child_process";

interface StreamingStatus {
  status: string;
  data: {
    overview: {
      status_text: string;
      status_icon: string;
      dependencies_ok: boolean;
      missing_deps: string[];
    };
    capabilities: {
      strategies: string[];
      buffer_strategies: string[];
      max_chunk_size: number;
      min_chunk_size: number;
    };
    current_config: {
      chunk_size_seconds: number;
      overlap_seconds: number;
      buffer_size_mb: number;
      max_memory_mb: number;
      strategy: string;
      buffer_strategy: string;
      prefetch_chunks: number;
      cache_enabled: boolean;
      quality_mode: boolean;
    };
  };
}

interface StreamingInsight {
  type: string;
  severity: string;
  title: string;
  description: string;
  suggestion: string;
  icon: string;
}

interface FileAnalysis {
  status: string;
  data: {
    file_info: {
      path: string;
      size_mb: number;
      exists: boolean;
    };
    audio_info: {
      duration?: number;
      sample_rate?: number;
      channels?: number;
      frames?: number;
      error?: string;
    };
    recommendation: {
      strategy: string;
      reason: string;
      config: any;
    };
  };
}

function executeStreamingCommand(command: string, args?: string): any {
  try {
    const argsStr = args ? ` ${args}` : '';
    const result = execSync(`cd "C:\\Users\\arthur.andrade\\OneDrive - Accenture\\Documents\\GitHub\\meetingscribe" && python src/core/streaming_cli.py ${command}${argsStr}`, {
      encoding: 'utf8',
      timeout: 30000
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Streaming command failed:', error);
    throw new Error(`Failed to execute streaming command: ${error}`);
  }
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function StreamingManagement() {
  const [streamingStatus, setStreamingStatus] = useState<StreamingStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStreamingStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = executeStreamingCommand('status');
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
      setStreamingStatus(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load streaming status');
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Failed to load streaming status"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStreamingStatus();
  }, []);

  if (isLoading) {
    return <Detail isLoading={true} markdown="Loading streaming status..." />;
  }

  if (error || !streamingStatus) {
    return (
      <Detail
        markdown={`# ❌ Error Loading Streaming Status\n\n${error || 'Unknown error occurred'}`}
        actions={
          <ActionPanel>
            <Action title="Retry" onAction={loadStreamingStatus} icon={Icon.RotateClockwise} />
          </ActionPanel>
        }
      />
    );
  }

  const { data } = streamingStatus;
  const { overview, capabilities, current_config } = data;

  const markdownContent = `
# ${overview.status_icon} Audio Streaming Management

## 📊 System Overview
- **Status**: ${overview.status_text}
- **Dependencies**: ${overview.dependencies_ok ? '✅ Available' : '❌ Missing'}
${overview.missing_deps.length > 0 ? `- **Missing**: ${overview.missing_deps.join(', ')}` : ''}

---

## 🛠️ Current Configuration
- **Strategy**: ${current_config.strategy}
- **Chunk Size**: ${current_config.chunk_size_seconds}s
- **Overlap**: ${current_config.overlap_seconds}s
- **Buffer Size**: ${current_config.buffer_size_mb} MB
- **Max Memory**: ${current_config.max_memory_mb} MB
- **Buffer Strategy**: ${current_config.buffer_strategy}
- **Prefetch Chunks**: ${current_config.prefetch_chunks}
- **Cache**: ${current_config.cache_enabled ? 'Enabled' : 'Disabled'}
- **Quality Mode**: ${current_config.quality_mode ? 'Enabled' : 'Disabled'}

---

## ⚡ Available Strategies
${capabilities.strategies.map(strategy => `- **${strategy}**`).join('\n')}

---

## 📦 Buffer Strategies
${capabilities.buffer_strategies.map(strategy => `- **${strategy}**`).join('\n')}

---

## 📏 Chunk Size Limits
- **Minimum**: ${capabilities.min_chunk_size}s
- **Maximum**: ${capabilities.max_chunk_size}s

---

*Last updated: ${new Date().toLocaleString()}*
  `;

  return (
    <Detail
      markdown={markdownContent}
      actions={
        <ActionPanel>
          <Action title="Refresh" onAction={loadStreamingStatus} icon={Icon.RotateClockwise} />
          <Action.Push 
            title="Analyze File" 
            target={<FileAnalyzer />} 
            icon={Icon.MagnifyingGlass} 
          />
          <Action.Push 
            title="Stream Test" 
            target={<StreamTester />} 
            icon={Icon.Play} 
          />
          <Action.Push 
            title="Streaming Insights" 
            target={<StreamingInsights />} 
            icon={Icon.LightBulb} 
          />
          <Action.Push 
            title="Benchmark Strategies" 
            target={<StrategyBenchmark />} 
            icon={Icon.BarChart} 
          />
        </ActionPanel>
      }
    />
  );
}

function FileAnalyzer() {
  const [analysis, setAnalysis] = useState<FileAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalyze = async (values: { filePath: string }) => {
    if (!values.filePath.trim()) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Please enter a file path"
      });
      return;
    }

    setIsLoading(true);
    
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Analyzing file..."
      });

      const result = executeStreamingCommand('analyze', `--file "${values.filePath}"`);
      
      if (result.status === 'success') {
        setAnalysis(result);
        await showToast({
          style: Toast.Style.Success,
          title: "Analysis Complete",
          message: "File analyzed successfully"
        });
      } else {
        throw new Error(result.message || 'Analysis failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Analysis Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (analysis) {
    const { data } = analysis;
    const { file_info, audio_info, recommendation } = data;

    const analysisMarkdown = `
# 🔍 File Analysis Results

## 📁 File Information
- **Path**: ${file_info.path}
- **Size**: ${file_info.size_mb} MB
- **Exists**: ${file_info.exists ? '✅' : '❌'}

## 🎵 Audio Information
${audio_info.error ? 
  `- **Error**: ${audio_info.error}` :
  `- **Duration**: ${audio_info.duration ? formatDuration(audio_info.duration) : 'Unknown'}
- **Sample Rate**: ${audio_info.sample_rate || 'Unknown'} Hz
- **Channels**: ${audio_info.channels || 'Unknown'}
- **Frames**: ${audio_info.frames?.toLocaleString() || 'Unknown'}`
}

## 💡 Streaming Recommendation
- **Strategy**: **${recommendation.strategy}**
- **Reason**: ${recommendation.reason}

### Recommended Configuration
- **Chunk Size**: ${recommendation.config.chunk_size_seconds}s
- **Overlap**: ${recommendation.config.overlap_seconds}s
- **Buffer Size**: ${recommendation.config.buffer_size_mb} MB
- **Max Memory**: ${recommendation.config.max_memory_mb} MB
- **Buffer Strategy**: ${recommendation.config.buffer_strategy}
- **Prefetch**: ${recommendation.config.prefetch_chunks} chunks
- **Quality Mode**: ${recommendation.config.quality_mode ? 'Enabled' : 'Disabled'}
    `;

    return (
      <Detail
        markdown={analysisMarkdown}
        actions={
          <ActionPanel>
            <Action title="Analyze Another" onAction={() => setAnalysis(null)} icon={Icon.ArrowLeft} />
            <Action.Push 
              title="Test This File" 
              target={<StreamTester initialFile={file_info.path} initialConfig={recommendation.config} />} 
              icon={Icon.Play} 
            />
          </ActionPanel>
        }
      />
    );
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm 
            title="Analyze File" 
            onSubmit={handleAnalyze}
            icon={Icon.MagnifyingGlass}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="filePath"
        title="Audio File Path"
        placeholder="Enter path to audio file..."
        info="Analyzes the file and recommends optimal streaming configuration"
      />
    </Form>
  );
}

function StreamTester({ initialFile, initialConfig }: { initialFile?: string, initialConfig?: any }) {
  const [testResult, setTestResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleTest = async (values: { filePath: string; configJson: string }) => {
    if (!values.filePath.trim()) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Please enter a file path"
      });
      return;
    }

    setIsLoading(true);
    
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Running streaming test..."
      });

      let args = `--file "${values.filePath}"`;
      if (values.configJson.trim()) {
        args += ` --config '${values.configJson}'`;
      }

      const result = executeStreamingCommand('test', args);
      
      if (result.status === 'success') {
        setTestResult(result);
        await showToast({
          style: Toast.Style.Success,
          title: "Test Complete",
          message: "Streaming test completed successfully"
        });
      } else {
        throw new Error(result.message || 'Test failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Test Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (testResult) {
    const { data } = testResult;
    const { test_results, streaming_stats, config_used } = data;

    const testMarkdown = `
# 🧪 Streaming Test Results

## ⏱️ Performance Results
- **Chunks Processed**: ${test_results.chunks_processed}
- **Test Duration**: ${test_results.test_duration_seconds}s
- **Audio Processed**: ${formatDuration(test_results.audio_duration_processed)}
- **Processing Speed**: ${test_results.processing_speed}x real-time

## 📊 Streaming Statistics
- **Total Chunks**: ${streaming_stats.total_chunks}
- **Processed Chunks**: ${streaming_stats.processed_chunks}
- **Cached Chunks**: ${streaming_stats.cached_chunks}
- **Memory Usage**: ${streaming_stats.memory_usage_mb.toFixed(1)} MB
- **Processing Time**: ${streaming_stats.processing_time.toFixed(3)}s
- **I/O Time**: ${streaming_stats.io_time.toFixed(3)}s
- **Cache Hit Rate**: ${streaming_stats.cache_hit_rate.toFixed(1)}%
- **Adaptive Adjustments**: ${streaming_stats.adaptive_adjustments}
- **Current Chunk Size**: ${streaming_stats.current_chunk_size}s

## ⚙️ Configuration Used
- **Strategy**: ${config_used.strategy}
- **Chunk Size**: ${config_used.chunk_size_seconds}s
- **Buffer Strategy**: ${config_used.buffer_strategy}
- **Buffer Size**: ${config_used.buffer_size_mb} MB
    `;

    return (
      <Detail
        markdown={testMarkdown}
        actions={
          <ActionPanel>
            <Action title="Test Another" onAction={() => setTestResult(null)} icon={Icon.ArrowLeft} />
          </ActionPanel>
        }
      />
    );
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm 
            title="Run Streaming Test" 
            onSubmit={handleTest}
            icon={Icon.Play}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="filePath"
        title="Audio File Path"
        placeholder="Enter path to audio file..."
        defaultValue={initialFile || ""}
        info="Path to the audio file to test streaming performance"
      />
      <Form.TextArea
        id="configJson"
        title="Configuration (JSON)"
        placeholder='{"chunk_size_seconds": 30, "strategy": "intelligent"}'
        defaultValue={initialConfig ? JSON.stringify(initialConfig, null, 2) : ""}
        info="Optional JSON configuration for streaming test"
      />
    </Form>
  );
}

function StreamingInsights() {
  const [insights, setInsights] = useState<{ insights: StreamingInsight[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        const data = executeStreamingCommand('insights');
        setInsights(data.data);
      } catch (err) {
        console.error('Failed to load streaming insights:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadInsights();
  }, []);

  if (isLoading || !insights) {
    return <Detail isLoading={true} markdown="Loading streaming insights..." />;
  }

  const markdown = `
# 💡 Streaming Performance Insights

${insights.insights?.length > 0 ?
  insights.insights.map((insight, i) => `
## ${insight.icon} ${insight.title}

**Type**: ${insight.type} | **Severity**: ${insight.severity.toUpperCase()}

${insight.description}

**💡 Suggestion**: ${insight.suggestion}

---
`).join('') :
  '✅ No specific insights available. Streaming system is performing well!'
}
  `;

  return <Detail markdown={markdown} />;
}

function StrategyBenchmark() {
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleBenchmark = async (values: { filePath: string }) => {
    if (!values.filePath.trim()) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Please enter a file path"
      });
      return;
    }

    setIsLoading(true);
    
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Running strategy benchmark..."
      });

      const result = executeStreamingCommand('benchmark', `--file "${values.filePath}"`);
      
      if (result.status === 'success') {
        setBenchmarkResult(result);
        await showToast({
          style: Toast.Style.Success,
          title: "Benchmark Complete",
          message: "Strategy benchmark completed successfully"
        });
      } else {
        throw new Error(result.message || 'Benchmark failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Benchmark Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (benchmarkResult) {
    const { data } = benchmarkResult;
    const { benchmark_results, best_strategy, best_time, recommendations } = data;

    const benchmarkMarkdown = `
# 📊 Strategy Benchmark Results

## 🏆 Best Strategy: **${best_strategy}**
**Best Time**: ${best_time}s

## 📈 Detailed Results

${Object.entries(benchmark_results).map(([strategy, result]: [string, any]) => {
  if (result.error) {
    return `### ❌ ${strategy}\n**Error**: ${result.error}\n`;
  } else {
    return `### ${strategy === best_strategy ? '🏆' : '📊'} ${strategy}
- **Duration**: ${result.duration_seconds}s
- **Chunks**: ${result.chunks_processed}
- **Cache Hit Rate**: ${result.stats?.cache_hit_rate?.toFixed(1) || 0}%
- **Adaptive Adjustments**: ${result.stats?.adaptive_adjustments || 0}

`;
  }
}).join('')}

## 💡 Recommendations
- **Fastest**: ${recommendations.fastest}
- **Most Adaptive**: ${recommendations.most_adaptive}
- **Memory Efficient**: ${recommendations.memory_efficient}
    `;

    return (
      <Detail
        markdown={benchmarkMarkdown}
        actions={
          <ActionPanel>
            <Action title="Benchmark Another" onAction={() => setBenchmarkResult(null)} icon={Icon.ArrowLeft} />
          </ActionPanel>
        }
      />
    );
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm 
            title="Run Benchmark" 
            onSubmit={handleBenchmark}
            icon={Icon.BarChart}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="filePath"
        title="Audio File Path"
        placeholder="Enter path to audio file..."
        info="Benchmarks all streaming strategies against this file"
      />
    </Form>
  );
}
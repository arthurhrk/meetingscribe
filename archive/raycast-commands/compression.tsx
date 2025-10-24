import { Action, ActionPanel, Detail, Icon, List, showToast, Toast, Form, confirmAlert, Alert } from "@raycast/api";
import { useEffect, useState } from "react";
import { execSync } from "child_process";

interface CompressionStatus {
  status: string;
  data: {
    overview: {
      status_text: string;
      status_icon: string;
      available_algorithms: number;
      dependencies_ok: boolean;
    };
    algorithms: {
      available: string[];
      recommended: {
        speed: string;
        balanced: string;
        compression: string;
      };
    };
    dependencies: {
      zstd: boolean;
      lz4: boolean;
    };
    config: {
      strategy: string;
      min_file_size: number;
      max_file_size: number;
      background_compression: boolean;
      analyze_before_compress: boolean;
      memory_limit_mb: number;
    };
    algorithm_stats: Record<string, {
      avg_compression_ratio: number;
      avg_speed_mbps: number;
      success_rate: number;
      total_uses: number;
    }>;
  };
}

interface CompressionInsight {
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
      size_bytes: number;
      size_mb: number;
      extension: string;
      file_type: string;
    };
    content_analysis: {
      entropy: number;
      repetition_ratio: number;
      text_ratio: number;
      binary_ratio: number;
    };
    recommendation: {
      algorithm: string;
      level: number;
      estimated_ratio: number;
      estimated_savings_percent: number;
      reason: string;
    };
    compressibility: string;
  };
}

function executeCompressionCommand(command: string, args?: string): any {
  try {
    const argsStr = args ? ` ${args}` : '';
    const result = execSync(`cd "C:\\Users\\arthur.andrade\\OneDrive - Accenture\\Documents\\GitHub\\meetingscribe" && python src/core/compression_cli.py ${command}${argsStr}`, {
      encoding: 'utf8',
      timeout: 30000
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Compression command failed:', error);
    throw new Error(`Failed to execute compression command: ${error}`);
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

export default function CompressionManagement() {
  const [compressionStatus, setCompressionStatus] = useState<CompressionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCompressionStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = executeCompressionCommand('status');
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
      setCompressionStatus(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load compression status');
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Failed to load compression status"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCompressionStatus();
  }, []);

  if (isLoading) {
    return <Detail isLoading={true} markdown="Loading compression status..." />;
  }

  if (error || !compressionStatus) {
    return (
      <Detail
        markdown={`# ❌ Error Loading Compression Status\n\n${error || 'Unknown error occurred'}`}
        actions={
          <ActionPanel>
            <Action title="Retry" onAction={loadCompressionStatus} icon={Icon.RotateClockwise} />
          </ActionPanel>
        }
      />
    );
  }

  const { data } = compressionStatus;
  const { overview, algorithms, dependencies, config, algorithm_stats } = data;

  const markdownContent = `
# ${overview.status_icon} Intelligent Compression Management

## 📊 System Overview
- **Status**: ${overview.status_text}
- **Available Algorithms**: ${overview.available_algorithms}
- **Dependencies**: ${overview.dependencies_ok ? '✅ All available' : '⚠️ Some missing'}

---

## ⚡ Available Algorithms
${algorithms.available.map(alg => `- **${alg}**`).join('\n')}

### 🎯 Recommendations
- **Speed Optimized**: ${algorithms.recommended.speed}
- **Balanced**: ${algorithms.recommended.balanced}
- **Maximum Compression**: ${algorithms.recommended.compression}

---

## 🔧 Dependencies Status
- **Zstandard (zstd)**: ${dependencies.zstd ? '✅ Available' : '❌ Missing'}
- **LZ4**: ${dependencies.lz4 ? '✅ Available' : '❌ Missing'}

---

## ⚙️ Current Configuration
- **Strategy**: ${config.strategy}
- **Min File Size**: ${formatBytes(config.min_file_size)}
- **Max File Size**: ${formatBytes(config.max_file_size)}
- **Background Compression**: ${config.background_compression ? 'Enabled' : 'Disabled'}
- **Auto-Analysis**: ${config.analyze_before_compress ? 'Enabled' : 'Disabled'}
- **Memory Limit**: ${config.memory_limit_mb} MB

---

## 📈 Algorithm Performance
${Object.entries(algorithm_stats).map(([alg, stats]) => `
### ${alg}
- **Avg Compression**: ${formatPercentage((1 - stats.avg_compression_ratio) * 100)} savings
- **Avg Speed**: ${stats.avg_speed_mbps.toFixed(1)} MB/s
- **Success Rate**: ${formatPercentage(stats.success_rate * 100)}
- **Total Uses**: ${stats.total_uses}
`).join('')}

---

*Last updated: ${new Date().toLocaleString()}*
  `;

  return (
    <Detail
      markdown={markdownContent}
      actions={
        <ActionPanel>
          <Action title="Refresh" onAction={loadCompressionStatus} icon={Icon.RotateClockwise} />
          <Action.Push 
            title="Analyze File" 
            target={<FileAnalyzer />} 
            icon={Icon.MagnifyingGlass} 
          />
          <Action.Push 
            title="Compress File" 
            target={<FileCompressor />} 
            icon={Icon.Box} 
          />
          <Action.Push 
            title="Benchmark Algorithms" 
            target={<AlgorithmBenchmark />} 
            icon={Icon.BarChart} 
          />
          <Action.Push 
            title="Compression Insights" 
            target={<CompressionInsights />} 
            icon={Icon.LightBulb} 
          />
          <Action.Push 
            title="Configuration" 
            target={<CompressionConfiguration />} 
            icon={Icon.Cog} 
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

      const result = executeCompressionCommand('analyze', `--file "${values.filePath}"`);
      
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
    const { file_info, content_analysis, recommendation, compressibility } = data;

    const analysisMarkdown = `
# 🔍 File Analysis Results

## 📁 File Information
- **Path**: ${file_info.path}
- **Size**: ${formatBytes(file_info.size_bytes)} (${file_info.size_mb.toFixed(1)} MB)
- **Type**: ${file_info.file_type}
- **Extension**: ${file_info.extension}

## 📊 Content Analysis
- **Entropy**: ${content_analysis.entropy.toFixed(3)} (randomness measure)
- **Repetition Ratio**: ${formatPercentage(content_analysis.repetition_ratio * 100)}
- **Text Content**: ${formatPercentage(content_analysis.text_ratio * 100)}
- **Binary Content**: ${formatPercentage(content_analysis.binary_ratio * 100)}

## 💡 Compression Assessment
- **Compressibility**: ${compressibility}
- **Estimated Savings**: ${formatPercentage(recommendation.estimated_savings_percent)}

## 🎯 Recommendations
- **Algorithm**: **${recommendation.algorithm}**
- **Level**: ${recommendation.level}
- **Estimated Ratio**: ${recommendation.estimated_ratio.toFixed(3)}
- **Reason**: ${recommendation.reason}

## 📈 Potential Results
- **Original Size**: ${formatBytes(file_info.size_bytes)}
- **Estimated Compressed**: ${formatBytes(file_info.size_bytes * recommendation.estimated_ratio)}
- **Estimated Savings**: ${formatBytes(file_info.size_bytes * (1 - recommendation.estimated_ratio))}
    `;

    return (
      <Detail
        markdown={analysisMarkdown}
        actions={
          <ActionPanel>
            <Action title="Analyze Another" onAction={() => setAnalysis(null)} icon={Icon.ArrowLeft} />
            <Action.Push 
              title="Compress This File" 
              target={<FileCompressor initialFile={file_info.path} initialAlgorithm={recommendation.algorithm} initialLevel={recommendation.level} />} 
              icon={Icon.Box} 
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
        title="File Path"
        placeholder="Enter path to file..."
        info="Analyzes file content and recommends optimal compression settings"
      />
    </Form>
  );
}

function FileCompressor({ initialFile, initialAlgorithm, initialLevel }: { initialFile?: string, initialAlgorithm?: string, initialLevel?: number }) {
  const [compressionResult, setCompressionResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCompress = async (values: { filePath: string; outputPath: string; algorithm: string; level: string }) => {
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
        title: "Compressing file..."
      });

      let args = `--file "${values.filePath}"`;
      if (values.outputPath.trim()) {
        args += ` --output "${values.outputPath}"`;
      }
      if (values.algorithm && values.algorithm !== 'auto') {
        args += ` --algorithm ${values.algorithm}`;
      }
      if (values.level && values.level !== 'auto') {
        args += ` --level ${values.level}`;
      }

      const result = executeCompressionCommand('compress', args);
      
      if (result.status === 'success') {
        setCompressionResult(result);
        await showToast({
          style: Toast.Style.Success,
          title: "Compression Complete",
          message: `Saved ${result.data.savings.percent}% space`
        });
      } else {
        throw new Error(result.message || 'Compression failed');
      }
    } catch (err) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Compression Failed",
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (compressionResult) {
    const { data } = compressionResult;
    const { compression_results, savings } = data;

    const resultMarkdown = `
# ✅ Compression Complete

## 📁 Files
- **Original**: ${data.original_path}
- **Compressed**: ${data.compressed_path}
${data.metadata_path ? `- **Metadata**: ${data.metadata_path}` : ''}

## 📊 Compression Results
- **Algorithm**: ${compression_results.algorithm}
- **Level**: ${compression_results.level}
- **Compression Time**: ${compression_results.compression_time}s
- **Speed**: ${compression_results.speed_mbps} MB/s
- **Efficiency Score**: ${compression_results.efficiency_score.toFixed(3)}

## 💰 Space Savings
- **Original Size**: ${formatBytes(compression_results.original_size)}
- **Compressed Size**: ${formatBytes(compression_results.compressed_size)}
- **Savings**: ${formatBytes(savings.bytes)} (${formatPercentage(savings.percent)})
- **Compression Ratio**: ${compression_results.compression_ratio.toFixed(3)}

## 🎯 Performance
- **File processed at**: ${compression_results.speed_mbps.toFixed(1)} MB/s
- **Efficiency score**: ${(compression_results.efficiency_score * 100).toFixed(1)}%
    `;

    return (
      <Detail
        markdown={resultMarkdown}
        actions={
          <ActionPanel>
            <Action title="Compress Another" onAction={() => setCompressionResult(null)} icon={Icon.ArrowLeft} />
            <Action.OpenWith path={data.compressed_path} />
            <Action.ShowInFinder path={data.compressed_path} />
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
            title="Compress File" 
            onSubmit={handleCompress}
            icon={Icon.Box}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="filePath"
        title="File Path"
        placeholder="Enter path to file..."
        defaultValue={initialFile || ""}
        info="Path to the file you want to compress"
      />
      <Form.TextField
        id="outputPath"
        title="Output Path (Optional)"
        placeholder="Auto-generated if empty..."
        info="Where to save the compressed file (optional)"
      />
      <Form.Dropdown
        id="algorithm"
        title="Algorithm"
        defaultValue={initialAlgorithm || "auto"}
        info="Compression algorithm to use"
      >
        <Form.Dropdown.Item value="auto" title="Auto (Recommended)" />
        <Form.Dropdown.Item value="gzip" title="GZIP (Balanced)" />
        <Form.Dropdown.Item value="lzma" title="LZMA (Best Compression)" />
        <Form.Dropdown.Item value="zstd" title="Zstandard (Modern)" />
        <Form.Dropdown.Item value="lz4" title="LZ4 (Fastest)" />
        <Form.Dropdown.Item value="bz2" title="BZ2 (Good Compression)" />
        <Form.Dropdown.Item value="zlib" title="ZLIB (Standard)" />
      </Form.Dropdown>
      <Form.Dropdown
        id="level"
        title="Compression Level"
        defaultValue={initialLevel?.toString() || "auto"}
        info="Higher levels = better compression, slower speed"
      >
        <Form.Dropdown.Item value="auto" title="Auto (Recommended)" />
        <Form.Dropdown.Item value="1" title="1 (Fastest)" />
        <Form.Dropdown.Item value="3" title="3 (Fast)" />
        <Form.Dropdown.Item value="6" title="6 (Balanced)" />
        <Form.Dropdown.Item value="7" title="7 (Good)" />
        <Form.Dropdown.Item value="9" title="9 (Best)" />
      </Form.Dropdown>
    </Form>
  );
}

function AlgorithmBenchmark() {
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleBenchmark = async (values: { filePath: string; sampleSize: string }) => {
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
        title: "Running algorithm benchmark..."
      });

      let args = `--file "${values.filePath}"`;
      if (values.sampleSize && values.sampleSize !== 'auto') {
        args += ` --sample-size ${values.sampleSize}`;
      }

      const result = executeCompressionCommand('benchmark', args);
      
      if (result.status === 'success') {
        setBenchmarkResult(result);
        await showToast({
          style: Toast.Style.Success,
          title: "Benchmark Complete",
          message: "Algorithm comparison completed"
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
    const { file_info, benchmark_results, recommendations } = data;

    const benchmarkMarkdown = `
# 📊 Algorithm Benchmark Results

## 📁 File Information
- **Path**: ${file_info.path}
- **Size**: ${formatBytes(file_info.size)}
- **Sample Size**: ${formatBytes(file_info.sample_size)}
${file_info.is_sample ? '- **Note**: Results based on sample, not entire file' : ''}

## 🏆 Recommendations
- **Best Overall**: ${recommendations.best_overall}
- **Best Compression**: ${recommendations.best_compression}
- **Fastest**: ${recommendations.fastest}

## 📈 Detailed Results

${Object.entries(benchmark_results).map(([algorithm, results]: [string, any]) => `
### ${algorithm.toUpperCase()}
- **Compression Ratio**: ${results.compression_ratio.toFixed(3)}
- **Savings**: ${formatPercentage(results.savings_percent)}
- **Compression Time**: ${results.compression_time.toFixed(3)}s
- **Decompression Time**: ${results.decompression_time.toFixed(3)}s
- **Speed**: ${results.speed_mbps.toFixed(1)} MB/s
- **Efficiency Score**: ${(results.efficiency_score * 100).toFixed(1)}%

`).join('')}

## 💡 Interpretation
- **Compression Ratio**: Lower is better (0.5 = 50% of original size)
- **Speed**: Higher is better (MB/s processed)
- **Efficiency**: Combines compression and speed (higher is better)
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
        title="File Path"
        placeholder="Enter path to file..."
        info="File to test all compression algorithms against"
      />
      <Form.Dropdown
        id="sampleSize"
        title="Sample Size"
        defaultValue="auto"
        info="How much of the file to test (larger = more accurate, slower)"
      >
        <Form.Dropdown.Item value="auto" title="Auto (Smart sampling)" />
        <Form.Dropdown.Item value="65536" title="64 KB (Fast)" />
        <Form.Dropdown.Item value="262144" title="256 KB (Balanced)" />
        <Form.Dropdown.Item value="1048576" title="1 MB (Accurate)" />
        <Form.Dropdown.Item value="4194304" title="4 MB (Very Accurate)" />
      </Form.Dropdown>
    </Form>
  );
}

function CompressionInsights() {
  const [insights, setInsights] = useState<{ insights: CompressionInsight[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        const data = executeCompressionCommand('insights');
        setInsights(data.data);
      } catch (err) {
        console.error('Failed to load compression insights:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadInsights();
  }, []);

  if (isLoading || !insights) {
    return <Detail isLoading={true} markdown="Loading compression insights..." />;
  }

  const markdown = `
# 💡 Compression Performance Insights

${insights.insights?.length > 0 ?
  insights.insights.map((insight, i) => `
## ${insight.icon} ${insight.title}

**Type**: ${insight.type} | **Severity**: ${insight.severity.toUpperCase()}

${insight.description}

**💡 Suggestion**: ${insight.suggestion}

---
`).join('') :
  '✅ No specific insights available. Compression system is performing optimally!'
}
  `;

  return <Detail markdown={markdown} />;
}

function CompressionConfiguration() {
  const [config, setConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const data = executeCompressionCommand('config');
        setConfig(data.data);
      } catch (err) {
        console.error('Failed to load compression config:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  if (isLoading || !config) {
    return <Detail isLoading={true} markdown="Loading compression configuration..." />;
  }

  const markdown = `
# ⚙️ Compression Configuration

## Current Settings
- **Strategy**: ${config.current_config.strategy}
- **Fallback Algorithm**: ${config.current_config.fallback_algorithm}
- **Fallback Level**: ${config.current_config.fallback_level}
- **Min File Size**: ${formatBytes(config.current_config.min_file_size)}
- **Max File Size**: ${formatBytes(config.current_config.max_file_size)}
- **Caching**: ${config.current_config.enable_caching ? 'Enabled' : 'Disabled'}
- **Background Compression**: ${config.current_config.background_compression ? 'Enabled' : 'Disabled'}
- **Auto-Analysis**: ${config.current_config.analyze_before_compress ? 'Enabled' : 'Disabled'}
- **Memory Limit**: ${config.current_config.memory_limit_mb} MB

## Available Options

### Algorithms
${config.available_algorithms.map((alg: string) => `- **${alg}**`).join('\n')}

### Strategies
${config.strategies.map((strategy: string) => `- **${strategy}**`).join('\n')}

### Compression Levels
${config.levels.map((level: number) => `- **${level}**`).join('\n')}

## 💡 Recommendations

### ${config.recommendations.for_speed}
For applications where speed is critical

### ${config.recommendations.for_size}
For maximum space savings

### ${config.recommendations.for_balance}
For general-purpose compression
  `;

  return <Detail markdown={markdown} />;
}
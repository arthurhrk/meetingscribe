import { Action, ActionPanel, Detail, Icon, List, showToast, Toast } from "@raycast/api";
import { useEffect, useState } from "react";
import { execSync } from "child_process";

interface BottleneckSummary {
  status: string;
  data: {
    overview: {
      status_icon: string;
      status_text: string;
      status_color: string;
      total_sessions: number;
      total_bottlenecks: number;
      avg_bottlenecks: string;
    };
    top_issues: Array<{
      type: string;
      count: number;
      description: string;
      suggestion: string;
    }>;
    severity_breakdown: Record<string, number>;
    recommendations: string[];
  };
}

interface ProfilingReport {
  session_id: string;
  operation: string;
  duration: string;
  start_time: string;
  bottlenecks_count: number;
  performance_grade: string;
  top_bottlenecks: Array<{
    type: string;
    severity: string;
    description: string;
    suggestion: string;
  }>;
}

interface Insight {
  type: string;
  severity: string;
  title: string;
  description: string;
  suggestion: string;
  icon: string;
}

function executeProfilingCommand(command: string, limit?: number): any {
  try {
    const limitArg = limit ? `--profiling-limit ${limit}` : '';
    const result = execSync(`cd "C:\\Users\\arthur.andrade\\OneDrive - Accenture\\Documents\\GitHub\\meetingscribe" && python main.py --profiling ${command} ${limitArg}`, {
      encoding: 'utf8',
      timeout: 10000
    });
    return JSON.parse(result);
  } catch (error) {
    console.error('Profiling command failed:', error);
    throw new Error(`Failed to execute profiling command: ${error}`);
  }
}

function formatSeverityIcon(severity: string): string {
  switch (severity) {
    case 'critical': return '🔴';
    case 'high': return '🟠';
    case 'medium': return '🟡';
    case 'low': return '🟢';
    case 'info': return 'ℹ️';
    default: return '❓';
  }
}

export default function ProfilingDashboard() {
  const [summaryData, setSummaryData] = useState<BottleneckSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSummaryData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = executeProfilingCommand('summary');
      
      if (data.status === 'error') {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
      setSummaryData(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profiling data');
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: "Failed to load profiling data"
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSummaryData();
  }, []);

  if (isLoading) {
    return <Detail isLoading={true} markdown="Loading profiling dashboard..." />;
  }

  if (error || !summaryData) {
    return (
      <Detail
        markdown={`# ❌ Error Loading Profiling Dashboard\n\n${error || 'Unknown error occurred'}`}
        actions={
          <ActionPanel>
            <Action title="Retry" onAction={loadSummaryData} icon={Icon.RotateClockwise} />
          </ActionPanel>
        }
      />
    );
  }

  const { data } = summaryData;
  const { overview } = data;

  const markdownContent = `
# ${overview.status_icon} Auto Profiling Dashboard

## 📊 Performance Overview
- **System Status**: ${overview.status_text}
- **Total Sessions Analyzed**: ${overview.total_sessions}
- **Total Bottlenecks Detected**: ${overview.total_bottlenecks}
- **Average Bottlenecks per Session**: ${overview.avg_bottlenecks}

---

## 🚨 Top Performance Issues
${data.top_issues?.length > 0 ? 
  data.top_issues.map((issue, i) => `
${i + 1}. **${issue.type.replace('_', ' ').toUpperCase()}** (${issue.count} occurrences)
   - ${issue.description}
   - 💡 **Suggestion**: ${issue.suggestion}
`).join('') :
  '✅ No significant performance issues detected!'
}

---

## 📈 Severity Breakdown
${Object.entries(data.severity_breakdown || {}).map(([severity, count]) => 
  `- **${severity.charAt(0).toUpperCase() + severity.slice(1)}**: ${count} issues`
).join('\n') || 'No severity data available'}

---

## 💡 Recommendations
${data.recommendations?.map(rec => `- ${rec}`).join('\n') || 'No recommendations available'}

---

*Analysis based on recent profiling sessions*
  `;

  return (
    <Detail
      markdown={markdownContent}
      actions={
        <ActionPanel>
          <Action title="Refresh" onAction={loadSummaryData} icon={Icon.RotateClockwise} />
          <Action.Push 
            title="Detailed Reports" 
            target={<DetailedReports />} 
            icon={Icon.Document} 
          />
          <Action.Push 
            title="Performance Insights" 
            target={<PerformanceInsights />} 
            icon={Icon.LightBulb} 
          />
          <Action.Push 
            title="Optimization Suggestions" 
            target={<OptimizationSuggestions />} 
            icon={Icon.Gear} 
          />
        </ActionPanel>
      }
    />
  );
}

function DetailedReports() {
  const [reportsData, setReportsData] = useState<{ reports: ProfilingReport[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadReports = async () => {
      try {
        const data = executeProfilingCommand('reports', 10);
        setReportsData(data.data);
      } catch (err) {
        console.error('Failed to load reports:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadReports();
  }, []);

  if (isLoading || !reportsData) {
    return <Detail isLoading={true} markdown="Loading detailed reports..." />;
  }

  const markdown = `
# 📋 Detailed Profiling Reports

${reportsData.reports?.length > 0 ?
  reportsData.reports.map((report, i) => `
## ${i + 1}. Session: ${report.operation} (${report.performance_grade})

- **Duration**: ${report.duration}
- **Start Time**: ${report.start_time}
- **Bottlenecks**: ${report.bottlenecks_count}

### Top Issues:
${report.top_bottlenecks?.map(b => `
- **${formatSeverityIcon(b.severity)} ${b.type}**: ${b.description}
  - 💡 ${b.suggestion}
`).join('') || 'No significant bottlenecks'}

---
`).join('') :
  '📝 No profiling reports available yet. Start some transcriptions to generate data!'
}
  `;

  return <Detail markdown={markdown} />;
}

function PerformanceInsights() {
  const [insightsData, setInsightsData] = useState<{ insights: Insight[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        const data = executeProfilingCommand('insights');
        setInsightsData(data.data);
      } catch (err) {
        console.error('Failed to load insights:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadInsights();
  }, []);

  if (isLoading || !insightsData) {
    return <Detail isLoading={true} markdown="Loading performance insights..." />;
  }

  const markdown = `
# 💡 Performance Insights

${insightsData.insights?.length > 0 ?
  insightsData.insights.map((insight, i) => `
## ${insight.icon} ${insight.title}

**Severity**: ${formatSeverityIcon(insight.severity)} ${insight.severity.toUpperCase()}

${insight.description}

**💡 Suggestion**: ${insight.suggestion}

---
`).join('') :
  '🎯 No specific insights available. Continue using the system to gather more data!'
}
  `;

  return <Detail markdown={markdown} />;
}

function OptimizationSuggestions() {
  const [suggestionsData, setSuggestionsData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const data = executeProfilingCommand('suggestions');
        setSuggestionsData(data.data);
      } catch (err) {
        console.error('Failed to load suggestions:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSuggestions();
  }, []);

  if (isLoading || !suggestionsData) {
    return <Detail isLoading={true} markdown="Loading optimization suggestions..." />;
  }

  const priorityIcon = (priority: string) => {
    switch (priority) {
      case 'high': return '🔴';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const markdown = `
# 🛠️ Optimization Suggestions

${suggestionsData.suggestions?.length > 0 ?
  suggestionsData.suggestions.map((suggestion: any, i: number) => `
## ${priorityIcon(suggestion.priority)} ${suggestion.title}

**Category**: ${suggestion.category}  
**Priority**: ${suggestion.priority.toUpperCase()}

${suggestion.description}

**🎯 Action**: ${suggestion.action}

---
`).join('') :
  '✅ System is running optimally! No immediate optimizations needed.'
}

*Total suggestions: ${suggestionsData.total_suggestions || 0}*
  `;

  return <Detail markdown={markdown} />;
}
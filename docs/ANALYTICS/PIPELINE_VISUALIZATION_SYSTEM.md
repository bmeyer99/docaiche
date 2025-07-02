# Real-Time Pipeline Visualization System Design for DocAIche

## Executive Summary

After extensive research, I'm proposing a **hybrid architecture** that combines:
- **OpenTelemetry** for distributed tracing and metrics collection
- **WebSocket** for real-time data streaming to the frontend
- **React Flow** for the pipeline visualization
- **Framer Motion** for smooth animations
- **Recharts** for metrics dashboards

This design provides both the metrics overview and individual query tracing you need, with a modern, sleek appearance and reasonable implementation complexity.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                       │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  React Flow     │  │   Recharts   │  │ Framer Motion│  │
│  │  Pipeline View  │  │ Metrics View │  │  Animations  │  │
│  └────────┬────────┘  └──────┬───────┘  └──────┬───────┘  │
│           └───────────────────┴─────────────────┘          │
│                              │                              │
│                    WebSocket Connection                     │
└──────────────────────────────┴──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                    API Server (FastAPI)                      │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ WebSocket       │  │ Metrics      │  │ Trace        │  │
│  │ Manager         │  │ Aggregator   │  │ Collector    │  │
│  └─────────────────┘  └──────────────┘  └──────────────┘  │
│           │                   │                  │          │
│  ┌────────┴───────────────────┴──────────────────┴──────┐  │
│  │          OpenTelemetry Collector (OTLP)              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │             Microservices                    │
        │  (Web Scraper, Content Processor, etc.)      │
        │   Each with OpenTelemetry SDK instrumented   │
        └──────────────────────────────────────────────┘
```

## 1. Protocol Selection: WebSocket

**Why WebSocket over gRPC:**
- WebSocket is a protocol allowing two-way communication between a client and a server. It's a popular choice for applications that handle real-time data
- Browser-native support (no proxy needed)
- Lower implementation complexity for frontend
- Perfect for event-driven updates
- established the connection to the server with the websocket. When the connection is established, the socket emits the consumer signal

**Implementation:**
```python
# API Server WebSocket endpoint
@app.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid4())
    
    # Subscribe to OpenTelemetry events
    await pipeline_monitor.add_client(client_id, websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            message = await websocket.receive_text()
            await handle_client_message(client_id, message)
    except WebSocketDisconnect:
        await pipeline_monitor.remove_client(client_id)
```

## 2. Metrics Collection with OpenTelemetry

OpenTelemetry is the mechanism by which application code is instrumented to help make a system observable

**Instrumentation for Each Service:**

```python
# In each microservice
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter, metrics_exporter
)

# Initialize telemetry
tracer = trace.get_tracer("docaiche.service_name")
meter = metrics.get_meter("docaiche.service_name")

# Metrics to collect
queue_length = meter.create_observable_gauge(
    name="service.queue.length",
    description="Current queue length",
    unit="1",
    callback=lambda: get_current_queue_length()
)

request_latency = meter.create_histogram(
    name="service.request.latency",
    description="Request processing latency",
    unit="ms"
)

# Trace decorator for key operations
@tracer.start_as_current_span("search_operation")
async def search_workspace(query: str, workspace: str):
    span = trace.get_current_span()
    span.set_attribute("query.text", query)
    span.set_attribute("workspace.name", workspace)
    
    # Your existing logic
    with request_latency.record(duration_ms):
        result = await perform_search(query, workspace)
    
    span.set_attribute("result.count", len(result))
    return result
```

## 3. Real-Time Pipeline Visualization

**Frontend Architecture using React Flow:**

```typescript
// Pipeline visualization component
import ReactFlow, { 
    Node, Edge, Background, Controls, MiniMap 
} from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';

interface ServiceNode extends Node {
    data: {
        label: string;
        metrics: {
            queueLength: number;
            avgLatency: number;
            throughput: number;
        };
        status: 'idle' | 'processing' | 'error';
        currentTrace?: string;
    };
}

const PipelineVisualizer: React.FC = () => {
    const [nodes, setNodes] = useState<ServiceNode[]>(initialNodes);
    const [edges, setEdges] = useState<Edge[]>(initialEdges);
    const [activeTraces, setActiveTraces] = useState<Map<string, TraceData>>();
    
    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:4000/ws/pipeline');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'metrics_update':
                    updateNodeMetrics(data.payload);
                    break;
                case 'trace_update':
                    animateTraceFlow(data.payload);
                    break;
                case 'service_status':
                    updateServiceStatus(data.payload);
                    break;
            }
        };
        
        return () => ws.close();
    }, []);
    
    return (
        <div className="h-screen bg-gray-900">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={customNodeTypes}
                edgeTypes={animatedEdgeTypes}
                fitView
                className="bg-gradient-to-br from-gray-900 to-gray-800"
            >
                <Background color="#374151" gap={16} />
                <Controls className="bg-gray-800 border-gray-700" />
                <MiniMap 
                    nodeColor={node => getNodeColor(node.data.status)}
                    className="bg-gray-800" 
                />
            </ReactFlow>
            
            {/* Floating metrics panel */}
            <MetricsPanel />
            
            {/* Active trace details */}
            <TraceDetailsPanel activeTraces={activeTraces} />
        </div>
    );
};
```

**Custom Node Component with Real-Time Updates:**

```typescript
const ServiceNodeComponent: React.FC<NodeProps> = ({ data }) => {
    return (
        <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ 
                scale: data.status === 'processing' ? 1.05 : 1,
                opacity: 1 
            }}
            className={`
                relative p-4 rounded-lg border-2 shadow-2xl
                ${data.status === 'idle' ? 'border-gray-600 bg-gray-800' : ''}
                ${data.status === 'processing' ? 'border-blue-500 bg-blue-900/50' : ''}
                ${data.status === 'error' ? 'border-red-500 bg-red-900/50' : ''}
            `}
        >
            <div className="text-white font-bold">{data.label}</div>
            
            {/* Real-time metrics */}
            <div className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between">
                    <span className="text-gray-400">Queue:</span>
                    <motion.span
                        key={data.metrics.queueLength}
                        initial={{ scale: 1.2, color: '#60A5FA' }}
                        animate={{ scale: 1, color: '#9CA3AF' }}
                    >
                        {data.metrics.queueLength}
                    </motion.span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-400">Latency:</span>
                    <span>{data.metrics.avgLatency}ms</span>
                </div>
            </div>
            
            {/* Active trace indicator */}
            <AnimatePresence>
                {data.currentTrace && (
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        exit={{ scale: 0 }}
                        className="absolute -top-2 -right-2 w-4 h-4 
                                 bg-blue-500 rounded-full animate-pulse"
                    />
                )}
            </AnimatePresence>
        </motion.div>
    );
};
```

## 4. Trace Animation System

**Visualizing Query Flow:**

```typescript
const animateTraceFlow = (trace: TraceData) => {
    // Create animated particle that follows the trace path
    const particle = {
        id: trace.traceId,
        path: trace.spans.map(span => ({
            nodeId: span.serviceName,
            timestamp: span.startTime,
            duration: span.duration,
            data: span.attributes
        }))
    };
    
    // Animate edge highlighting
    trace.spans.forEach((span, index) => {
        if (index < trace.spans.length - 1) {
            const edgeId = `${span.serviceName}-${trace.spans[index + 1].serviceName}`;
            
            setTimeout(() => {
                highlightEdge(edgeId, span.attributes);
            }, calculateDelay(span.startTime, trace.startTime));
        }
    });
    
    // Show trace results at each node
    showTraceResults(particle);
};

// Custom animated edge
const AnimatedEdge: FC<EdgeProps> = ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    style = {},
    data,
}) => {
    const [isActive, setIsActive] = useState(false);
    
    useEffect(() => {
        if (data?.active) {
            setIsActive(true);
            setTimeout(() => setIsActive(false), 1000);
        }
    }, [data?.active]);
    
    return (
        <>
            <BaseEdge {...props} />
            <AnimatePresence>
                {isActive && (
                    <motion.circle
                        r="4"
                        fill="#3B82F6"
                        initial={{ offsetDistance: '0%' }}
                        animate={{ offsetDistance: '100%' }}
                        transition={{ duration: 0.5, ease: "easeInOut" }}
                    >
                        <animateMotion
                            dur="0.5s"
                            path={`M ${sourceX},${sourceY} L ${targetX},${targetY}`}
                        />
                    </motion.circle>
                )}
            </AnimatePresence>
        </>
    );
};
```

## 5. Metrics Dashboard Integration

```typescript
const MetricsPanel: React.FC = () => {
    const [metrics, setMetrics] = useState<ServiceMetrics[]>([]);
    
    return (
        <motion.div
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            className="absolute left-4 top-4 w-80 bg-gray-800/90 
                     backdrop-blur rounded-lg shadow-2xl p-4"
        >
            <h3 className="text-white font-bold mb-4">System Metrics</h3>
            
            {/* Real-time throughput chart */}
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={metrics}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" />
                    <YAxis stroke="#9CA3AF" />
                    <Tooltip 
                        contentStyle={{ 
                            backgroundColor: '#1F2937',
                            border: '1px solid #374151'
                        }}
                    />
                    <Line 
                        type="monotone" 
                        dataKey="throughput" 
                        stroke="#3B82F6"
                        strokeWidth={2}
                        dot={false}
                    />
                </LineChart>
            </ResponsiveContainer>
            
            {/* Service health indicators */}
            <div className="mt-4 grid grid-cols-2 gap-2">
                {services.map(service => (
                    <ServiceHealthCard 
                        key={service.id}
                        service={service}
                        metrics={metrics[service.id]}
                    />
                ))}
            </div>
        </motion.div>
    );
};
```

## 6. Implementation Timeline & Complexity

### Phase 1: OpenTelemetry Integration (1 week)
- Add OTLP instrumentation to all services
- Set up collector configuration
- Basic metrics export

### Phase 2: WebSocket Infrastructure (1 week)
- WebSocket manager in API server
- Event aggregation from OpenTelemetry
- Basic frontend connection

### Phase 3: React Flow Pipeline (2 weeks)
- Node and edge components
- Real-time updates
- Basic animations

### Phase 4: Polish & Advanced Features (1 week)
- Smooth animations with Framer Motion
- Advanced trace visualization
- Performance optimization

## 7. Key Metrics to Collect

**Per Service:**
- Queue length (gauge, updated every 1s)
- Request latency (histogram, per request)
- Throughput (counter, requests/second)
- Error rate (counter, errors/minute)
- Memory usage (gauge, every 5s)
- Active connections (gauge, every 1s)

**Per Request Trace:**
- Total duration
- Service hops with timing
- Cache hit/miss at each stage
- Result quality scores
- Enrichment decisions

## 8. Modern UI/UX Features

- **Glass morphism** effects for panels
- **Particle animations** for active traces
- **Heat maps** for service load
- **Smooth transitions** between states
- **Dark theme** with neon accents
- **Interactive tooltips** with detailed metrics
- **Time travel** to replay past traces
- **3D perspective** option for the pipeline

## Summary

This architecture provides:
- ✅ Real-time visualization of both metrics and individual queries
- ✅ Modern, sleek appearance with smooth animations
- ✅ Reasonable implementation complexity
- ✅ Strong community support (OpenTelemetry, React Flow, WebSocket)
- ✅ Scalable to handle many concurrent traces
- ✅ Extensible for future features

The combination of OpenTelemetry for instrumentation and WebSocket for real-time updates gives you the best of both worlds: comprehensive data collection with efficient delivery to the frontend.

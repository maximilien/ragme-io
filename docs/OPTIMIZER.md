# RAGme Optimization Tools

RAGme includes powerful optimization tools to help fine-tune system performance and improve query relevance. These tools use systematic testing and binary search algorithms to find optimal configuration values.

## 🎯 Query Threshold Optimizer

The Query Threshold Optimizer automatically finds the optimal `text_relevance_threshold` value for your specific document collection and use cases.

### Overview

The optimizer performs a binary search across a configurable range of threshold values, testing each value against predefined query scenarios to find the best balance between recall and precision.

### Features

- **🔍 Binary Search Algorithm**: Efficiently explores threshold ranges to find optimal values
- **🧪 Multi-Query Testing**: Tests against multiple query scenarios for comprehensive evaluation
- **📊 Score-Based Evaluation**: Evaluates threshold performance using success/failure metrics
- **🔄 Automatic Restart**: Automatically restarts backend services after each threshold change
- **📝 Config Updates**: Programmatically updates `config.yaml` with optimal values
- **🔍 Verbose Output**: Optional detailed logging for debugging and analysis

### Usage

#### Command Line Interface

```bash
# Basic usage with default range (0.2 to 0.8)
./tools/optimize.sh query-threshold

# Custom range
./tools/optimize.sh query-threshold 0.3 0.9

# With verbose output
./tools/optimize.sh query-threshold --verbose
```

#### Direct Python Script

```bash
# Basic usage
python tools/threshold_optimizer.py

# Custom range
python tools/threshold_optimizer.py 0.3 0.9

# With verbose output
python tools/threshold_optimizer.py 0.3 0.9 --verbose
```

### Test Cases

The optimizer evaluates thresholds against these predefined test cases:

1. **"what is ragme"** - Should find RAGme documents
   - Expected content: ["ragme", "retrieval", "generation", "agent"]

2. **"who is maximilien"** - Should find maximilien.org document
   - Expected content: ["maximilien", "haiti", "photography", "website"]

3. **"photography"** - Should find photography-related content
   - Expected content: ["maximilien", "photography", "travel"]

### Algorithm Details

#### Binary Search Process

1. **Initial Testing**: Tests both endpoints of the specified range
2. **Iterative Search**: Performs binary search to narrow down optimal range
3. **Nearby Testing**: Tests values around the best found threshold
4. **Final Evaluation**: Confirms optimal threshold with final test

#### Scoring System

- **Success Criteria**: Query response contains expected keywords
- **Score Calculation**: Number of successful queries out of total test cases
- **Best Threshold**: Highest score achieved across all tested values

#### Precision and Convergence

- **Default Precision**: 0.05 (5% threshold difference)
- **Convergence**: Stops when high-low range is less than precision
- **Nearby Testing**: Tests ±0.05 and ±0.02 around best value

### Configuration

#### Required Documents

The optimizer assumes these documents are present in your collection:
- `ragme-io.pdf` - Contains RAGme project information
- `maximilien.org` - Contains personal information

If these documents are missing, the optimizer will still work but may not achieve optimal results.

#### Environment Requirements

- **Backend Running**: RAGme backend must be running on `localhost:8021`
- **Vector Database**: Configured and accessible
- **Test Documents**: Relevant documents should be in the collection

### Output and Results

#### Console Output

```
🎯 Starting binary search for optimal threshold...
📏 Range: 0.2 to 0.8
🎯 Precision: 0.05
📋 Test cases: 3

📍 Testing low endpoint (0.2)...
🧪 Testing threshold: 0.2
📝 Threshold: 0.2
🔄 Restarting backend...

🔍 Testing: Should find RAGme documents
   Query: 'what is ragme'
   ✅ PASS: Found expected content

🔍 Testing: Should find maximilien.org document
   Query: 'who is maximilien'
   ✅ PASS: Found expected content

🔍 Testing: Should find photography-related content
   Query: 'photography'
   ❌ FAIL: Missing expected content

📊 Threshold 0.2 Score: 2/3

...

🎯 OPTIMAL THRESHOLD: 0.35
🏆 BEST SCORE: 3/3
📊 ITERATIONS: 4
```

#### Final Results

The optimizer provides:
- **Optimal Threshold**: Best performing threshold value
- **Best Score**: Number of successful test cases
- **Iteration Count**: Number of binary search iterations
- **Configuration Update**: Automatically updates `config.yaml`

### Advanced Usage

#### Custom Test Cases

To modify test cases, edit the `test_cases` list in `tools/threshold_optimizer.py`:

```python
self.test_cases = [
    {
        "query": "your custom query",
        "expected": ["expected", "keywords"],
        "description": "Description of what this should find"
    },
    # Add more test cases...
]
```

#### Precision Adjustment

Modify the `precision` value in the `ThresholdOptimizer` class:

```python
def __init__(self, min_threshold: float = 0.2, max_threshold: float = 0.8, verbose: bool = False):
    self.precision = 0.02  # More precise search (2% difference)
```

#### Custom Evaluation Logic

Override the `evaluate_threshold` method to implement custom scoring:

```python
def evaluate_threshold(self, threshold: float) -> Tuple[int, Dict[str, Any]]:
    # Custom evaluation logic
    # Return (score, results_dict)
```

### Troubleshooting

#### Common Issues

1. **Backend Not Running**
   ```
   ❌ Error: RAGme backend is not running on localhost:8021
   ```
   **Solution**: Start the backend with `./start.sh`

2. **Missing Documents**
   ```
   ❌ FAIL: Missing expected content
   ```
   **Solution**: Ensure test documents are in your collection

3. **Low Scores Across All Thresholds**
   - Check if documents are properly indexed
   - Verify vector database configuration
   - Review search implementation

#### Debug Mode

Use verbose output to see detailed information:

```bash
python tools/threshold_optimizer.py --verbose
```

This shows:
- Raw query responses
- Score calculation details
- Search method information
- Configuration changes

### Integration with CI/CD

The optimizer can be integrated into automated testing:

```bash
# Example CI script
./tools/optimize.sh query-threshold 0.3 0.7
if [ $? -eq 0 ]; then
    echo "Optimization successful"
    # Continue with deployment
else
    echo "Optimization failed"
    exit 1
fi
```

### Future Enhancements

Planned improvements for the optimization tools:

1. **Multi-Parameter Optimization**: Optimize multiple parameters simultaneously
2. **Custom Test Suites**: User-defined test case collections
3. **Performance Metrics**: Response time and resource usage optimization
4. **Machine Learning**: ML-based parameter optimization
5. **Visualization**: Charts and graphs of optimization results

## 🔧 Tool Architecture

### File Structure

```
tools/
├── optimize.sh              # Main CLI interface
├── threshold_optimizer.py   # Core optimization logic
└── ...                     # Other optimization tools
```

### Class Structure

```python
class ThresholdOptimizer:
    def __init__(self, min_threshold, max_threshold, verbose)
    def update_threshold(self, threshold)
    def restart_backend(self)
    def test_query(self, query, expected_contains)
    def evaluate_threshold(self, threshold)
    def binary_search_threshold(self)
```

### Dependencies

- **requests**: HTTP client for API testing
- **subprocess**: Process management for backend restart
- **argparse**: Command-line argument parsing
- **json**: Response parsing and configuration updates

## 📚 Related Documentation

- **[Configuration Guide](CONFIG.md)** - Understanding config.yaml settings
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Vector database configuration
- **[Process Management](PROCESS_MANAGEMENT.md)** - Backend service management
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions

## 🤝 Contributing

To contribute to the optimization tools:

1. **Add New Optimizers**: Create new optimization scripts for other parameters
2. **Improve Algorithms**: Enhance the binary search or add new optimization methods
3. **Extend Test Cases**: Add more comprehensive test scenarios
4. **Add Visualizations**: Create charts and graphs for optimization results

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

#!/usr/bin/env python3

import sys
import os
import json
import subprocess
import time
import argparse
import requests
from typing import Tuple, Dict, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class ThresholdOptimizer:
    def __init__(self, min_threshold: float = 0.2, max_threshold: float = 0.8, verbose: bool = False):
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.precision = 0.05
        self.verbose = verbose
        self.best_threshold = None
        self.best_score = -1
        self.best_results = None
        
        # Test cases for evaluation
        self.test_cases = [
            {
                "query": "what is ragme",
                "expected": ["ragme", "retrieval", "generation", "agent"],
                "description": "Should find RAGme documents"
            },
            {
                "query": "who is maximilien", 
                "expected": ["maximilien", "haiti", "photography", "website"],
                "description": "Should find maximilien.org document"
            },
            {
                "query": "photography",
                "expected": ["maximilien", "photography", "travel"],
                "description": "Should find photography-related content"
            }
        ]

    def update_threshold(self, threshold: float) -> None:
        """Update the threshold in config.yaml"""
        config_path = "config.yaml"
        
        # Read the current config
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        # Find and update the text_relevance_threshold line
        for i, line in enumerate(lines):
            if "text_relevance_threshold:" in line:
                lines[i] = f"  text_relevance_threshold: {threshold}  # Minimum similarity score for text documents (0.0 to 1.0)\n"
                break
        
        # Write back the config
        with open(config_path, 'w') as f:
            f.writelines(lines)
        
        if self.verbose:
            print(f"📝 Updated threshold to: {threshold}")
        else:
            print(f"📝 Threshold: {threshold}")

    def restart_backend(self) -> None:
        """Restart the backend services"""
        print("🔄 Restarting backend...")
        subprocess.run(["./start.sh", "restart-backend"], check=True, capture_output=True)
        time.sleep(3)  # Wait for services to start

    def test_query(self, query: str, expected_contains: list = None) -> Tuple[bool, str]:
        """Test a query and return success status"""
        try:
            result = subprocess.run([
                "curl", "-X", "POST", "http://localhost:8021/query",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"query": query}),
                "-s"
            ], capture_output=True, text=True, check=True)
            
            response = json.loads(result.stdout)
            response_text = response.get("response", "").lower()
            
            if expected_contains:
                success = any(phrase in response_text for phrase in expected_contains)
                return success, response_text[:150] + "..." if len(response_text) > 150 else response_text
            else:
                return True, response_text[:150] + "..." if len(response_text) > 150 else response_text
                
        except Exception as e:
            print(f"❌ Error testing query: {e}")
            return False, ""

    def evaluate_threshold(self, threshold: float) -> Tuple[int, Dict[str, Any]]:
        """Evaluate a threshold value with test queries"""
        print(f"\n{'='*70}")
        print(f"🧪 Testing threshold: {threshold}")
        print(f"{'='*70}")
        
        # Update config and restart
        self.update_threshold(threshold)
        self.restart_backend()
        
        results = {}
        total_score = 0
        
        for test_case in self.test_cases:
            query = test_case["query"]
            expected = test_case["expected"]
            description = test_case["description"]
            
            print(f"\n🔍 Testing: {description}")
            print(f"   Query: '{query}'")
            
            success, response = self.test_query(query, expected)
            results[query] = {
                "success": success,
                "response": response,
                "expected": expected
            }
            
            if success:
                print(f"   ✅ PASS: Found expected content")
                total_score += 1
            else:
                print(f"   ❌ FAIL: Missing expected content")
                print(f"   Response: {response}")
            
            time.sleep(1)  # Small delay between queries
        
        print(f"\n📊 Threshold {threshold} Score: {total_score}/{len(self.test_cases)}")
        return total_score, results

    def binary_search_threshold(self) -> Tuple[float, int]:
        """Perform binary search for optimal threshold"""
        print("🎯 Starting binary search for optimal threshold...")
        print(f"📏 Range: {self.min_threshold} to {self.max_threshold}")
        print(f"🎯 Precision: {self.precision}")
        print(f"📋 Test cases: {len(self.test_cases)}")
        
        low = self.min_threshold
        high = self.max_threshold
        iterations = 0
        
        # Test the endpoints first
        print(f"\n📍 Testing low endpoint ({low})...")
        score_low, results_low = self.evaluate_threshold(low)
        
        print(f"\n📍 Testing high endpoint ({high})...")
        score_high, results_high = self.evaluate_threshold(high)
        
        if score_low > self.best_score:
            self.best_score = score_low
            self.best_threshold = low
            self.best_results = results_low
        
        if score_high > self.best_score:
            self.best_score = score_high
            self.best_threshold = high
            self.best_results = results_high
        
        # Binary search
        while high - low > self.precision:
            iterations += 1
            mid = (low + high) / 2
            print(f"\n🔄 Iteration {iterations}: Testing midpoint {mid:.3f}")
            
            score_mid, results_mid = self.evaluate_threshold(mid)
            
            if score_mid > self.best_score:
                self.best_score = score_mid
                self.best_threshold = mid
                self.best_results = results_mid
            
            # Decide which half to explore
            if score_mid >= score_low:
                # Mid is better than low, explore upper half
                low = mid
                score_low = score_mid
            else:
                # Mid is worse than low, explore lower half
                high = mid
                score_high = score_mid
        
        # Test a few more values around the best found
        print(f"\n🏆 Best threshold found: {self.best_threshold:.3f} (score: {self.best_score})")
        print("🔍 Testing nearby values...")
        
        nearby_values = [
            self.best_threshold - 0.05,
            self.best_threshold + 0.05,
            self.best_threshold - 0.02,
            self.best_threshold + 0.02
        ]
        
        for value in nearby_values:
            if self.min_threshold <= value <= self.max_threshold:
                print(f"\n📍 Testing nearby value: {value:.3f}")
                score, results = self.evaluate_threshold(value)
                
                if score > self.best_score:
                    self.best_score = score
                    self.best_threshold = value
                    self.best_results = results
        
        # Final result
        print(f"\n{'='*70}")
        print(f"🎯 OPTIMAL THRESHOLD: {self.best_threshold:.3f}")
        print(f"🏆 BEST SCORE: {self.best_score}/{len(self.test_cases)}")
        print(f"📊 ITERATIONS: {iterations}")
        print(f"{'='*70}")
        
        # Set the optimal threshold
        self.update_threshold(self.best_threshold)
        self.restart_backend()
        
        print(f"\n✅ Final test with optimal threshold {self.best_threshold}:")
        final_score, final_results = self.evaluate_threshold(self.best_threshold)
        
        return self.best_threshold, self.best_score

def main():
    parser = argparse.ArgumentParser(description='Optimize RAGme query threshold')
    parser.add_argument('min_threshold', nargs='?', type=float, default=0.2, 
                       help='Minimum threshold value (default: 0.2)')
    parser.add_argument('max_threshold', nargs='?', type=float, default=0.8,
                       help='Maximum threshold value (default: 0.8)')
    
    args = parser.parse_args()
    
    optimizer = ThresholdOptimizer(args.min_threshold, args.max_threshold)
    optimal_threshold, score = optimizer.binary_search_threshold()
    
    print(f"\n🎯 Optimization complete!")
    print(f"📊 Optimal threshold: {optimal_threshold:.3f}")
    print(f"🏆 Best score: {score}/{len(optimizer.test_cases)}")
    print(f"💾 Threshold has been updated in config.yaml")

if __name__ == "__main__":
    main()

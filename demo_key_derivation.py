#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Key Derivation Research Demonstration
========================================================

File: demo_key_derivation.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Comprehensive demonstration of key derivation research capabilities

This script demonstrates the advanced key derivation research features,
including master key derivation, multi-card analysis, and real-world
EMV cryptographic pattern detection.
"""

import sys
import os
import time
import logging
from typing import Dict, List, Any
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from key_derivation_research_clean import KeyDerivationAnalyzer, CardCryptoProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_realistic_test_scenarios():
    """Create realistic test scenarios for key derivation research."""
    scenarios = []
    
    # Scenario 1: Same issuer, potentially shared master key
    scenario1 = {
        'name': 'Same Issuer Analysis',
        'description': 'Multiple cards from same issuer to test for shared master keys',
        'cards': [
            {
                'card_id': 'visa_bank_001',
                'pan': '4123456789012345',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '201',
                'pin': '1234',
                'application_cryptogram': 'A1B2C3D4E5F67890',
                'atc': '0001',
                'unpredictable_number': '12345678',
                'issuer_application_data': '1234567890ABCDEF'
            },
            {
                'card_id': 'visa_bank_002', 
                'pan': '4123456789012346',
                'pan_sequence': '00',
                'expiry_date': '1226',
                'service_code': '201',
                'pin': '5678',
                'application_cryptogram': 'A1B2C3D4E5F67891',  # Similar pattern
                'atc': '0002',
                'unpredictable_number': '87654321',
                'issuer_application_data': '1234567890ABCDEF'
            },
            {
                'card_id': 'visa_bank_003',
                'pan': '4123456789012347',
                'pan_sequence': '00', 
                'expiry_date': '1227',
                'service_code': '201',
                'pin': '9999',
                'application_cryptogram': 'A1B2C3D4E5F67892',  # Similar pattern
                'atc': '0003',
                'unpredictable_number': '11223344',
                'issuer_application_data': '1234567890ABCDEF'
            }
        ]
    }
    scenarios.append(scenario1)
    
    # Scenario 2: Mixed issuers, should show low correlation
    scenario2 = {
        'name': 'Mixed Issuer Analysis',
        'description': 'Cards from different issuers to test specificity',
        'cards': [
            {
                'card_id': 'visa_001',
                'pan': '4111111111111111',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '101',
                'pin': '1111',
                'application_cryptogram': 'F1E2D3C4B5A69876',
                'atc': '0001',
                'unpredictable_number': 'ABCDEF12'
            },
            {
                'card_id': 'mastercard_001',
                'pan': '5555555555554444',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '101',
                'pin': '2222',
                'application_cryptogram': '1234567890ABCDEF',
                'atc': '0001',
                'unpredictable_number': '87654321'
            },
            {
                'card_id': 'amex_001',
                'pan': '378282246310005',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '101',
                'pin': '3333',
                'application_cryptogram': 'FEDCBA0987654321',
                'atc': '0001',
                'unpredictable_number': '13579BDF'
            }
        ]
    }
    scenarios.append(scenario2)
    
    # Scenario 3: PIN-based vulnerability test
    scenario3 = {
        'name': 'PIN-based Vulnerability Analysis',
        'description': 'Cards with known PINs to test PIN-based key derivation',
        'cards': [
            {
                'card_id': 'pin_test_001',
                'pan': '4000000000000002',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '101',
                'pin': '0000',  # Weak PIN
                'application_cryptogram': '0000111122223333',
                'atc': '0001',
                'unpredictable_number': '00000000'
            },
            {
                'card_id': 'pin_test_002',
                'pan': '4000000000000003',
                'pan_sequence': '00',
                'expiry_date': '1225',
                'service_code': '101',
                'pin': '1234',  # Common PIN
                'application_cryptogram': '1234567890123456',
                'atc': '0001',
                'unpredictable_number': '12345678'
            },
            {
                'card_id': 'pin_test_003',
                'pan': '4000000000000004',
                'pan_sequence': '00',
                'expiry_date': '1225', 
                'service_code': '101',
                'pin': '1111',  # Weak PIN
                'application_cryptogram': '1111222233334444',
                'atc': '0001',
                'unpredictable_number': '11111111'
            }
        ]
    }
    scenarios.append(scenario3)
    
    return scenarios

def run_key_derivation_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single key derivation scenario."""
    logger.info(f"\n{'='*60}")
    logger.info(f"RUNNING SCENARIO: {scenario['name']}")
    logger.info(f"Description: {scenario['description']}")
    logger.info(f"{'='*60}")
    
    # Initialize analyzer
    analyzer = KeyDerivationAnalyzer()
    
    # Add card profiles
    for card_data in scenario['cards']:
        profile = CardCryptoProfile(
            card_id=card_data['card_id'],
            pan=card_data['pan'],
            pan_sequence=card_data.get('pan_sequence', '00'),
            expiry_date=card_data.get('expiry_date', ''),
            service_code=card_data.get('service_code', ''),
            pin=card_data.get('pin'),
            application_cryptogram=card_data.get('application_cryptogram'),
            atc=card_data.get('atc'),
            unpredictable_number=card_data.get('unpredictable_number'),
            issuer_application_data=card_data.get('issuer_application_data'),
            extraction_timestamp=time.time()
        )
        
        analyzer.add_card_profile(profile)
        logger.info(f"Added card: {profile.card_id} (PAN: {profile.pan[:6]}...{profile.pan[-4:]})")
        
    # Run analysis
    logger.info("\nRunning comprehensive key derivation analysis...")
    analysis_results = analyzer.analyze_key_patterns()
    
    # Display results
    logger.info("\nAnalysis Results:")
    logger.info("-" * 40)
    
    for method, result in analysis_results.get('derivation_attempts', {}).items():
        if 'error' in result:
            logger.info(f"❌ {method}: ERROR - {result['error']}")
        else:
            success_prob = result.get('success_probability', 0)
            confidence = result.get('confidence_score', 0)
            patterns = len(result.get('pattern_matches', []))
            
            if success_prob > 0.5:
                status = "🔴 HIGH RISK"
            elif success_prob > 0.2:
                status = "🟡 MEDIUM RISK"
            else:
                status = "🟢 LOW RISK"
                
            logger.info(f"{status} {method}:")
            logger.info(f"  Success Probability: {success_prob:.2%}")
            logger.info(f"  Confidence Score: {confidence:.2f}")
            logger.info(f"  Patterns Found: {patterns}")
            
    # Generate scenario-specific insights
    insights = generate_scenario_insights(scenario, analysis_results)
    
    scenario_results = {
        'scenario_name': scenario['name'],
        'cards_analyzed': len(scenario['cards']),
        'analysis_results': analysis_results,
        'insights': insights,
        'timestamp': time.time()
    }
    
    return scenario_results

def generate_scenario_insights(scenario: Dict[str, Any], results: Dict[str, Any]) -> List[str]:
    """Generate insights specific to the scenario."""
    insights = []
    
    scenario_name = scenario['name']
    derivation_attempts = results.get('derivation_attempts', {})
    
    if 'Same Issuer' in scenario_name:
        # Check for same issuer patterns
        master_key_result = derivation_attempts.get('common_master_key', {})
        if master_key_result.get('success_probability', 0) > 0.3:
            insights.append("🔍 SAME ISSUER VULNERABILITY: Common master key patterns detected")
            insights.append("💡 RECOMMENDATION: Review issuer key management practices")
        else:
            insights.append("✅ SAME ISSUER SECURITY: No obvious master key sharing detected")
            
    elif 'Mixed Issuer' in scenario_name:
        # Check that different issuers don't share patterns
        overall_success = max(
            result.get('success_probability', 0) 
            for result in derivation_attempts.values() 
            if isinstance(result, dict)
        )
        
        if overall_success < 0.1:
            insights.append("✅ ISSUER ISOLATION: Different issuers show distinct patterns")
        else:
            insights.append("⚠️ CROSS-ISSUER PATTERNS: Unexpected similarities detected")
            
    elif 'PIN-based' in scenario_name:
        # Check for PIN-based vulnerabilities
        pin_result = derivation_attempts.get('pin_based_derivation', {})
        if pin_result.get('success_probability', 0) > 0.2:
            insights.append("🔓 PIN VULNERABILITY: PIN-based key derivation possible")
            insights.append("💡 RECOMMENDATION: Strengthen PIN-based cryptography")
        else:
            insights.append("🔒 PIN SECURITY: PIN-based attacks show low success rate")
            
    # General recommendations
    recommendations = results.get('recommendations', [])
    for rec in recommendations:
        insights.append(f"📋 RECOMMENDATION: {rec}")
        
    return insights

def run_comprehensive_demonstration():
    """Run comprehensive key derivation research demonstration."""
    logger.info("🔬 NFSP00F3R V5.00 - KEY DERIVATION RESEARCH DEMONSTRATION")
    logger.info("=" * 80)
    logger.info("This demonstration showcases advanced EMV key derivation research capabilities")
    logger.info("including master key derivation, multi-card analysis, and pattern detection.\n")
    
    # Get test scenarios
    scenarios = create_realistic_test_scenarios()
    
    all_results = []
    
    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        logger.info(f"\n🧪 SCENARIO {i} of {len(scenarios)}")
        
        try:
            scenario_results = run_key_derivation_scenario(scenario)
            all_results.append(scenario_results)
            
            # Brief pause between scenarios
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Scenario {i} failed: {e}")
            continue
            
    # Generate comprehensive summary
    logger.info(f"\n{'='*80}")
    logger.info("COMPREHENSIVE DEMONSTRATION SUMMARY")
    logger.info(f"{'='*80}")
    
    total_cards = sum(result['cards_analyzed'] for result in all_results)
    logger.info(f"📊 Total Cards Analyzed: {total_cards}")
    logger.info(f"📋 Scenarios Completed: {len(all_results)}")
    
    # Analyze overall risk levels
    high_risk_scenarios = 0
    medium_risk_scenarios = 0
    
    for result in all_results:
        derivation_attempts = result['analysis_results'].get('derivation_attempts', {})
        max_success = max(
            attempt.get('success_probability', 0) 
            for attempt in derivation_attempts.values() 
            if isinstance(attempt, dict)
        )
        
        if max_success > 0.5:
            high_risk_scenarios += 1
        elif max_success > 0.2:
            medium_risk_scenarios += 1
            
    logger.info(f"🔴 High Risk Scenarios: {high_risk_scenarios}")
    logger.info(f"🟡 Medium Risk Scenarios: {medium_risk_scenarios}")
    logger.info(f"🟢 Low Risk Scenarios: {len(all_results) - high_risk_scenarios - medium_risk_scenarios}")
    
    # Key findings
    logger.info("\n🔍 KEY FINDINGS:")
    logger.info("-" * 20)
    
    all_insights = []
    for result in all_results:
        all_insights.extend(result.get('insights', []))
        
    # Show unique insights
    unique_insights = list(set(all_insights))
    for insight in unique_insights[:10]:  # Top 10 insights
        logger.info(f"  • {insight}")
        
    # Overall security assessment
    logger.info("\n🛡️ OVERALL SECURITY ASSESSMENT:")
    logger.info("-" * 30)
    
    if high_risk_scenarios > 0:
        logger.info("🔴 CRITICAL: High-risk vulnerabilities detected in key derivation")
        logger.info("   IMMEDIATE ACTION REQUIRED: Review cryptographic implementations")
    elif medium_risk_scenarios > 0:
        logger.info("🟡 MODERATE: Some patterns detected that warrant investigation")
        logger.info("   RECOMMENDED: Enhanced monitoring and key rotation")
    else:
        logger.info("🟢 SECURE: No significant key derivation vulnerabilities detected")
        logger.info("   STATUS: Current implementations appear robust")
        
    # Save detailed results
    output_file = f"key_derivation_demo_results_{int(time.time())}.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        logger.info(f"\n📄 Detailed results saved to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        
    logger.info(f"\n{'='*80}")
    logger.info("KEY DERIVATION RESEARCH DEMONSTRATION COMPLETE")
    logger.info(f"{'='*80}")
    
    return all_results

def main():
    """Main demonstration function."""
    try:
        logger.info("Initializing key derivation research demonstration...")
        
        # Check if key derivation module is available
        try:
            from key_derivation_research_clean import KeyDerivationAnalyzer
            logger.info("✅ Key derivation research module loaded successfully")
        except ImportError as e:
            logger.error(f"❌ Key derivation research module not available: {e}")
            return False
            
        # Run comprehensive demonstration
        results = run_comprehensive_demonstration()
        
        logger.info(f"\n🎯 DEMONSTRATION COMPLETE: Analyzed {sum(r['cards_analyzed'] for r in results)} cards across {len(results)} scenarios")
        
        return True
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

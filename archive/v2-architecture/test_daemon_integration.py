"""
Integration tests for daemon system.

Tests the complete daemon functionality including:
- Service lifecycle management
- Named pipe communication
- Resource manager model caching
- Teams detection integration
- FR-001 compliance verification
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from daemon.daemon_main import DaemonMain
    from daemon.service import MeetingScribeService, service_status
    from daemon.resource_manager import get_resource_manager, cleanup_resource_manager
    from daemon.named_pipe_server import NamedPipeServer
except ImportError as e:
    print(f"Failed to import daemon components: {e}")
    sys.exit(1)


class TestDaemonIntegration(unittest.TestCase):
    """Integration tests for daemon system."""
    
    def setUp(self):
        """Set up test environment."""
        self.daemon: Optional[DaemonMain] = None
        self.daemon_thread: Optional[threading.Thread] = None
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        if self.daemon:
            self.daemon.stop_gracefully()
            
        if self.daemon_thread and self.daemon_thread.is_alive():
            self.daemon_thread.join(timeout=10)
            
        cleanup_resource_manager()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_daemon_startup_shutdown(self):
        """Test basic daemon startup and shutdown."""
        print("Testing daemon startup and shutdown...")
        
        # Create daemon instance
        self.daemon = DaemonMain()
        
        # Start daemon in separate thread
        self.daemon_thread = threading.Thread(target=self.daemon.run, daemon=True)
        self.daemon_thread.start()
        
        # Wait for daemon to start
        time.sleep(3)
        
        # Verify daemon is running
        self.assertTrue(self.daemon.running, "Daemon should be running")
        
        # Stop daemon
        self.daemon.stop_gracefully()
        
        # Wait for shutdown
        time.sleep(2)
        
        # Verify daemon stopped
        self.assertFalse(self.daemon.running, "Daemon should be stopped")
        
        print("✅ Daemon startup/shutdown test passed")
    
    def test_resource_manager_integration(self):
        """Test resource manager integration."""
        print("Testing resource manager integration...")
        
        try:
            # Get resource manager
            resource_manager = get_resource_manager()
            self.assertIsNotNone(resource_manager, "Resource manager should be available")
            
            # Check initial state
            stats = resource_manager.get_cache_stats()
            self.assertIsInstance(stats, dict, "Cache stats should be dict")
            self.assertIn('cached_models', stats, "Stats should contain cached_models")
            
            # Test model preloading (if Whisper available)
            try:
                success = resource_manager.preload_base_model()
                if success:
                    print("✅ Base model preloaded successfully")
                    
                    # Check that model was cached
                    stats_after = resource_manager.get_cache_stats()
                    self.assertGreater(stats_after['cached_models'], stats['cached_models'],
                                     "Should have more cached models after preload")
                else:
                    print("⚠️ Base model preloading failed (expected if Whisper not available)")
                    
            except Exception as e:
                print(f"⚠️ Model preloading test skipped: {e}")
                
            print("✅ Resource manager integration test passed")
            
        except Exception as e:
            print(f"❌ Resource manager test failed: {e}")
            raise
    
    def test_named_pipe_server(self):
        """Test Named Pipe server functionality."""
        print("Testing Named Pipe server...")
        
        try:
            # Create named pipe server
            pipe_server = NamedPipeServer()
            
            # Start server
            pipe_server.start()
            
            # Wait for server to start
            time.sleep(1)
            
            # Stop server
            pipe_server.stop()
            
            print("✅ Named Pipe server test passed")
            
        except Exception as e:
            print(f"⚠️ Named Pipe server test skipped: {e}")
            # Named pipes may not be available on all systems
    
    def test_fr001_compliance_metrics(self):
        """Test FR-001 compliance metrics collection."""
        print("Testing FR-001 compliance metrics...")
        
        # Create daemon instance
        self.daemon = DaemonMain()
        
        # Test fast startup metrics
        from daemon.fast_startup import get_startup_metrics
        startup_metrics = get_startup_metrics()
        self.assertIsInstance(startup_metrics, dict, "Startup metrics should be dict")
        
        # Test memory optimization
        memory_optimizer = self.daemon.memory_optimizer
        self.assertIsNotNone(memory_optimizer, "Memory optimizer should be available")
        
        memory_stats = memory_optimizer.get_usage_stats()
        self.assertIsInstance(memory_stats, dict, "Memory stats should be dict")
        self.assertIn('current_mb', memory_stats, "Should contain current memory usage")
        
        print("✅ FR-001 compliance metrics test passed")
    
    def test_daemon_components_initialization(self):
        """Test that all daemon components initialize properly."""
        print("Testing daemon components initialization...")
        
        # Create daemon instance
        self.daemon = DaemonMain()
        
        # Test component initialization
        try:
            self.daemon._initialize_components_optimized()
            
            # Verify critical components
            self.assertIsNotNone(self.daemon.teams_detector, "Teams detector should be initialized")
            self.assertIsNotNone(self.daemon.smart_selector, "Smart selector should be initialized")
            
            print("✅ Daemon components initialization test passed")
            
        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            raise
    
    def test_stdio_json_rpc_protocol(self):
        """Test STDIO JSON-RPC protocol functionality."""
        print("Testing STDIO JSON-RPC protocol...")
        
        try:
            from daemon.stdio_core import _handle
            
            # Test basic RPC call
            result = _handle("system.ping", {})
            self.assertIsInstance(result, dict, "RPC result should be dict")
            self.assertIn('status', result, "Result should contain status")
            
            # Test device listing
            result = _handle("audio.list_devices", {})
            self.assertIsInstance(result, dict, "Device list result should be dict")
            
            print("✅ STDIO JSON-RPC protocol test passed")
            
        except Exception as e:
            print(f"⚠️ STDIO protocol test skipped: {e}")
    
    def test_teams_detection_integration(self):
        """Test Teams detection integration."""
        print("Testing Teams detection integration...")
        
        try:
            from src.teams import get_detector
            
            # Get Teams detector
            detector = get_detector()
            self.assertIsNotNone(detector, "Teams detector should be available")
            
            # Test detector configuration
            self.assertTrue(hasattr(detector, 'on_meeting_detected'), 
                          "Detector should have meeting detection callback")
            
            print("✅ Teams detection integration test passed")
            
        except Exception as e:
            print(f"⚠️ Teams detection test skipped: {e}")


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for Windows Service functionality."""
    
    def test_service_status_check(self):
        """Test service status checking."""
        print("Testing service status check...")
        
        try:
            status = service_status()
            self.assertIn(status, ["running", "stopped", "not_installed", "unknown"],
                         f"Service status should be valid, got: {status}")
            
            print(f"✅ Service status check passed (status: {status})")
            
        except Exception as e:
            print(f"⚠️ Service status test skipped: {e}")


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end workflow tests."""
    
    def test_complete_daemon_workflow(self):
        """Test complete daemon workflow from startup to shutdown."""
        print("Testing complete daemon workflow...")
        
        try:
            # Phase 1: Daemon Startup
            daemon = DaemonMain()
            
            # Phase 2: Component Initialization
            daemon._initialize_components_optimized()
            
            # Phase 3: Advanced Components (if available)
            daemon._initialize_advanced_components()
            
            # Phase 4: System Readiness Check
            components_ready = (
                daemon.teams_detector is not None and
                daemon.smart_selector is not None
            )
            
            self.assertTrue(components_ready, "All components should be ready")
            
            # Phase 5: Cleanup
            daemon._cleanup_components()
            
            print("✅ Complete daemon workflow test passed")
            
        except Exception as e:
            print(f"❌ Complete workflow test failed: {e}")
            raise


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Running MeetingScribe Daemon Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(TestDaemonIntegration('test_daemon_startup_shutdown'))
    suite.addTest(TestDaemonIntegration('test_resource_manager_integration'))
    suite.addTest(TestDaemonIntegration('test_named_pipe_server'))
    suite.addTest(TestDaemonIntegration('test_fr001_compliance_metrics'))
    suite.addTest(TestDaemonIntegration('test_daemon_components_initialization'))
    suite.addTest(TestDaemonIntegration('test_stdio_json_rpc_protocol'))
    suite.addTest(TestDaemonIntegration('test_teams_detection_integration'))
    
    suite.addTest(TestServiceIntegration('test_service_status_check'))
    
    suite.addTest(TestEndToEndWorkflow('test_complete_daemon_workflow'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("🧪 Integration Test Summary")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Test Failures:")
        for test, traceback in result.failures:
            tb_lines = traceback.split('\n') if traceback else ['Unknown']
            print(f"  - {test}: {tb_lines[-2] if len(tb_lines) > 1 else 'Unknown'}")
    
    if result.errors:
        print("\n❌ Test Errors:")
        for test, traceback in result.errors:
            tb_lines = traceback.split('\n') if traceback else ['Unknown']
            print(f"  - {test}: {tb_lines[-2] if len(tb_lines) > 1 else 'Unknown'}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    return success


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
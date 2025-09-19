"""
Test grader for verifying the grading system works.
checks if a test field was added to the MinIO admin API response.
"""

import os
import subprocess
import time
import requests
import json
from typing import Dict, Tuple

from .spec import EnvironmentState, Grade, SubGrade, Grader


class TestFieldGrader(Grader):
    """
    test grader to check if 'test_field' was added to admin API response.
    """
    name = "TestFieldGrader"
    
    @classmethod
    def compute_score(
        cls,
        state: EnvironmentState,
        working_dir: str = "/build/minio"
    ) -> Tuple[float, Dict]:
        """
        if 'test_field': 'grading_works' exists in /minio/admin/v3/info response.
        
        Returns:
            score 1.0 if field exists with correct value
            score 0.5 if field exists with wrong value  
            score 0.0 if field doesn't exist
        """
        metadata = {}
        
        try:
            subprocess.run(
                ["rm", "-f", "test_*.go"],
                cwd=working_dir,
                capture_output=True
            )
            
            build_result = subprocess.run(
                ["go", "build", "-o", "minio"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if build_result.returncode != 0:
                metadata["error"] = f"Build failed: {build_result.stderr}"
                return (0.0, metadata)
            
            subprocess.run(["pkill", "minio"], capture_output=True)
            time.sleep(1)
            
            env = {
                "MINIO_ROOT_USER": "admin",
                "MINIO_ROOT_PASSWORD": "password"
            }
            subprocess.Popen(
                ["./minio", "server", "/data"],
                cwd=working_dir,
                env={**os.environ, **env},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)

            from datetime import datetime
            import hashlib
            import hmac
            
            # AWS Signature V4 parameters
            access_key = "admin"
            secret_key = "password"
            region = "us-east-1"
            service = "s3"

            now = datetime.utcnow()
            amz_date = now.strftime("%Y%m%dT%H%M%SZ")
            date_stamp = now.strftime("%Y%m%d")
            
            method = "GET"
            canonical_uri = "/minio/admin/v3/info"
            canonical_querystring = ""
            payload_hash = hashlib.sha256(b"").hexdigest()
            
            canonical_headers = f"host:localhost:9000\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
            signed_headers = "host;x-amz-content-sha256;x-amz-date"
            
            canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

            algorithm = "AWS4-HMAC-SHA256"
            credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
            string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
            
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
            
            k_date = sign(f"AWS4{secret_key}".encode('utf-8'), date_stamp)
            k_region = sign(k_date, region)
            k_service = sign(k_region, service)
            k_signing = sign(k_service, "aws4_request")
            signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            
            authorization_header = f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
            
            headers = {
                "Authorization": authorization_header,
                "X-Amz-Content-Sha256": payload_hash,
                "X-Amz-Date": amz_date
            }
            
            response = requests.get(
                "http://localhost:9000/minio/admin/v3/info",
                headers=headers,
                timeout=5
            )
            
            metadata["status_code"] = response.status_code
            metadata["auth_method"] = "aws_signature_v4"
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if "test_field" in data:
                        if data["test_field"] == "grading_works":
                            metadata["test_field_found"] = True
                            metadata["test_field_value"] = data["test_field"]
                            metadata["result"] = "SUCCESS: test_field added with correct value"
                            return (1.0, metadata)
                        else:
                            metadata["test_field_found"] = True
                            metadata["test_field_value"] = data["test_field"]
                            metadata["result"] = f"PARTIAL: test_field exists but wrong value: {data['test_field']}"
                            return (0.5, metadata)
                    else:
                        metadata["test_field_found"] = False
                        metadata["result"] = "FAIL: test_field not found in response"
                        metadata["response_keys"] = list(data.keys())[:10]
                        return (0.0, metadata)
                        
                except json.JSONDecodeError:
                    metadata["error"] = "Response is not valid JSON"
                    metadata["response_text"] = response.text[:200]
                    return (0.0, metadata)
            else:
                metadata["error"] = f"Failed to get admin info: {response.status_code}"
                metadata["response"] = response.text[:200]
                return (0.0, metadata)
                
        except subprocess.TimeoutExpired:
            metadata["error"] = "Build timeout"
            return (0.0, metadata)
        except requests.exceptions.RequestException as e:
            metadata["error"] = f"Request failed: {str(e)}"
            return (0.0, metadata)
        except Exception as e:
            metadata["error"] = f"Test failed: {str(e)}"
            return (0.0, metadata)
        finally:
            subprocess.run(["pkill", "minio"], capture_output=True)


def test_grading(
    state: EnvironmentState,
    working_dir: str = "/build/minio"
) -> Grade:
    """
    Grade the test task and check if test_field was added to admin API.
    """
    return Grade.from_subscores([
        TestFieldGrader.grade(
            state=state,
            weight=1.0,
            working_dir=working_dir
        )
    ])
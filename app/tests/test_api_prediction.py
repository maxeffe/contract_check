import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
import json
import io

class TestPredictionBasic:
    """Test basic prediction endpoints"""

    def test_predict_success(self, client, auth_headers, sample_document_text):
        """Test successful prediction request"""
        # First top up balance to have funds for prediction
        client.post("/wallet/topup", json={"amount": 100.0}, headers=auth_headers)
        
        prediction_data = {
            "document_text": sample_document_text,
            "filename": "test_contract.txt",
            "language": "RU",
            "model_name": "default_model",
            "summary_depth": "BULLET"
        }
        
        with patch('services.prediction_service.process_prediction_request') as mock_predict:
            mock_predict.return_value = {
                "message": "Prediction queued successfully",
                "job_id": 1,
                "document_id": 1,
                "status": "PENDING",
                "cost": 10.0,
                "tokens_processed": 100
            }
            
            response = client.post("/predict", json=prediction_data, headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job_id" in data
        assert "document_id" in data
        assert "status" in data
        assert "cost" in data
        assert "tokens_processed" in data

    def test_predict_no_auth(self, client, sample_document_text):
        """Test prediction without authentication"""
        prediction_data = {
            "document_text": sample_document_text,
            "filename": "test_contract.txt"
        }
        
        response = client.post("/predict", json=prediction_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_predict_insufficient_balance(self, client, auth_headers, sample_document_text):
        """Test prediction with insufficient balance"""
        prediction_data = {
            "document_text": sample_document_text,
            "filename": "test_contract.txt",
            "language": "RU",
            "model_name": "default_model",
            "summary_depth": "BULLET"
        }
        
        with patch('services.prediction_service.process_prediction_request') as mock_predict:
            mock_predict.side_effect = ValueError("Insufficient balance: required 10.0, available 0")
            
            response = client.post("/predict", json=prediction_data, headers=auth_headers)
            
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Insufficient balance" in response.json()["detail"]

    def test_predict_invalid_data(self, client, auth_headers):
        """Test prediction with invalid data"""
        # Missing required fields
        response = client.post("/predict", json={}, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Empty document text
        prediction_data = {
            "document_text": "",
            "filename": "test.txt"
        }
        response = client.post("/predict", json=prediction_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestPredictionFileUpload:
    """Test file upload prediction endpoints"""

    def test_predict_upload_success(self, client, auth_headers):
        """Test successful file upload prediction"""
        # Top up balance
        client.post("/wallet/topup", json={"amount": 100.0}, headers=auth_headers)
        
        # Create test file content
        file_content = b"Test contract content for analysis"
        
        with patch('services.prediction_service.process_prediction_request') as mock_predict, \
             patch('services.document_processor.document_processor.validate_file') as mock_validate, \
             patch('services.document_processor.document_processor.process_file') as mock_process:
            
            mock_validate.return_value = (True, "Valid file")
            mock_process.return_value = ("Processed text content", True)
            mock_predict.return_value = {
                "message": "Prediction queued successfully",
                "job_id": 1,
                "document_id": 1,
                "status": "PENDING",
                "cost": 10.0,
                "tokens_processed": 100
            }
            
            files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
            data = {"language": "RU"}
            
            response = client.post("/predict/upload", files=files, data=data, headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "job_id" in response_data
        assert "filename" in response_data
        assert response_data["filename"] == "test.txt"

    def test_predict_upload_no_auth(self, client):
        """Test file upload without authentication"""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post("/predict/upload", files=files)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_predict_upload_invalid_file_type(self, client, auth_headers):
        """Test upload with invalid file type"""
        file_content = b"Invalid content"
        files = {"file": ("test.xyz", io.BytesIO(file_content), "application/unknown")}
        
        response = client.post("/predict/upload", files=files, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in response.json()["detail"]

    def test_predict_upload_processing_failure(self, client, auth_headers):
        """Test file upload with processing failure"""
        file_content = b"Test content"
        
        with patch('services.document_processor.document_processor.validate_file') as mock_validate, \
             patch('services.document_processor.document_processor.process_file') as mock_process:
            
            mock_validate.return_value = (True, "Valid file")
            mock_process.return_value = ("", False)  # Processing failed
            
            files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
            response = client.post("/predict/upload", files=files, headers=auth_headers)
            
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDocumentManagement:
    """Test document management endpoints"""

    def test_get_documents_empty(self, client, auth_headers):
        """Test getting documents for new user"""
        response = client.get("/documents", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "total_count" in data
        assert len(data["documents"]) == 0
        assert data["total_count"] == 0

    def test_get_documents_with_data(self, client, auth_headers):
        """Test getting documents after creating some"""
        # Mock document service to return test documents
        with patch('services.crud.document.get_user_documents') as mock_get_docs, \
             patch('services.crud.document.count_user_documents') as mock_count:
            
            mock_document = MagicMock()
            mock_document.id = 1
            mock_document.user_id = 1
            mock_document.filename = "test_contract.txt"
            mock_document.pages = 1
            mock_document.language = "RU"
            mock_document.uploaded_at = "2024-01-01T00:00:00"
            
            mock_get_docs.return_value = [mock_document]
            mock_count.return_value = 1
            
            response = client.get("/documents", headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["total_count"] == 1
        assert data["documents"][0]["filename"] == "test_contract.txt"

    def test_get_documents_pagination(self, client, auth_headers):
        """Test document pagination"""
        response = client.get("/documents?limit=5&skip=0", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get("/documents?limit=10&skip=5", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_documents_no_auth(self, client):
        """Test getting documents without auth"""
        response = client.get("/documents")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_document_details_not_found(self, client, auth_headers):
        """Test getting details for non-existent document"""
        with patch('services.crud.document.get_document_by_id') as mock_get_doc:
            mock_get_doc.return_value = None
            
            response = client.get("/documents/999", headers=auth_headers)
            
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_document_details_access_denied(self, client, auth_headers):
        """Test getting details for document belonging to another user"""
        with patch('services.crud.document.get_document_by_id') as mock_get_doc:
            mock_document = MagicMock()
            mock_document.id = 1
            mock_document.user_id = 999  # Different user
            
            mock_get_doc.return_value = mock_document
            
            response = client.get("/documents/1", headers=auth_headers)
            
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPredictionHistory:
    """Test prediction history endpoints"""

    def test_get_history_empty(self, client, auth_headers):
        """Test getting empty prediction history"""
        with patch('services.crud.mljob.get_user_jobs') as mock_get_jobs, \
             patch('services.crud.mljob.count_user_jobs') as mock_count:
            
            mock_get_jobs.return_value = []
            mock_count.return_value = 0
            
            response = client.get("/history", headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "jobs" in data
        assert "total_count" in data
        assert len(data["jobs"]) == 0

    def test_get_history_with_data(self, client, auth_headers):
        """Test getting prediction history with data"""
        with patch('services.crud.mljob.get_user_jobs') as mock_get_jobs, \
             patch('services.crud.mljob.count_user_jobs') as mock_count, \
             patch('services.crud.mljob.get_job_risk_clauses') as mock_get_clauses:
            
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.document_id = 1
            mock_job.model_id = 1
            mock_job.status = "COMPLETED"
            mock_job.summary_depth = "BULLET"
            mock_job.used_credits = 10.0
            mock_job.summary_text = "Test summary"
            mock_job.risk_score = 0.7
            mock_job.started_at = "2024-01-01T00:00:00"
            mock_job.finished_at = "2024-01-01T00:05:00"
            
            mock_get_jobs.return_value = [mock_job]
            mock_count.return_value = 1
            mock_get_clauses.return_value = []
            
            response = client.get("/history", headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "COMPLETED"

    def test_get_history_pagination(self, client, auth_headers):
        """Test prediction history pagination"""
        response = client.get("/history?limit=5&skip=0", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_get_history_no_auth(self, client):
        """Test getting history without auth"""
        response = client.get("/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJobDetails:
    """Test job details endpoints"""

    def test_get_job_details_success(self, client, auth_headers):
        """Test getting job details successfully"""
        with patch('services.crud.mljob.get_job_by_id') as mock_get_job, \
             patch('services.crud.document.get_document_by_id') as mock_get_doc, \
             patch('services.crud.mljob.get_job_risk_clauses') as mock_get_clauses:
            
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.document_id = 1
            mock_job.status = "COMPLETED"
            
            mock_document = MagicMock()
            mock_document.user_id = 1  # Same as current user
            
            mock_get_job.return_value = mock_job
            mock_get_doc.return_value = mock_document
            mock_get_clauses.return_value = []
            
            response = client.get("/jobs/1", headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK

    def test_get_job_details_not_found(self, client, auth_headers):
        """Test getting non-existent job details"""
        with patch('services.crud.mljob.get_job_by_id') as mock_get_job:
            mock_get_job.return_value = None
            
            response = client.get("/jobs/999", headers=auth_headers)
            
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_job_details_access_denied(self, client, auth_headers):
        """Test getting job details for job belonging to another user"""
        with patch('services.crud.mljob.get_job_by_id') as mock_get_job, \
             patch('services.crud.document.get_document_by_id') as mock_get_doc:
            
            mock_job = MagicMock()
            mock_job.document_id = 1
            
            mock_document = MagicMock()
            mock_document.user_id = 999  # Different user
            
            mock_get_job.return_value = mock_job
            mock_get_doc.return_value = mock_document
            
            response = client.get("/jobs/1", headers=auth_headers)
            
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestModelManagement:
    """Test model management endpoints"""

    def test_get_available_models(self, client):
        """Test getting available ML models"""
        with patch('services.crud.model.get_active_models') as mock_get_models:
            mock_model = MagicMock()
            mock_model.id = 1
            mock_model.name = "test_model"
            mock_model.price_per_token = 0.001
            mock_model.active = True
            
            mock_get_models.return_value = [mock_model]
            
            response = client.get("/models")
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_model"
        assert data[0]["active"] is True


class TestCostEstimation:
    """Test cost estimation endpoints"""

    def test_estimate_cost_json(self, client, auth_headers, sample_document_text):
        """Test cost estimation with JSON input"""
        with patch('services.crud.model.get_active_models') as mock_get_models, \
             patch('models.document.Document.count_tokens') as mock_count_tokens:
            
            mock_model = MagicMock()
            mock_model.name = "test_model"
            mock_model.price_per_token = 0.001
            
            mock_get_models.return_value = [mock_model]
            mock_count_tokens.return_value = 100
            
            response = client.post("/estimate", 
                                 json={"document_text": sample_document_text},
                                 headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "token_count" in data
        assert "estimated_cost" in data
        assert "model_name" in data
        assert "price_per_token" in data
        assert data["token_count"] == 100
        assert data["estimated_cost"] == 0.1  # 100 * 0.001

    def test_estimate_cost_file_upload(self, client, auth_headers):
        """Test cost estimation with file upload"""
        file_content = b"Test contract content"
        
        with patch('services.document_processor.document_processor.validate_file') as mock_validate, \
             patch('services.document_processor.document_processor.process_file') as mock_process, \
             patch('services.crud.model.get_active_models') as mock_get_models, \
             patch('models.document.Document.count_tokens') as mock_count_tokens:
            
            mock_validate.return_value = (True, "Valid")
            mock_process.return_value = ("Processed content", True)
            
            mock_model = MagicMock()
            mock_model.name = "test_model"
            mock_model.price_per_token = 0.001
            
            mock_get_models.return_value = [mock_model]
            mock_count_tokens.return_value = 50
            
            files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
            
            response = client.post("/estimate", files=files, headers=auth_headers)
            
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["token_count"] == 50

    def test_estimate_cost_no_text(self, client, auth_headers):
        """Test cost estimation without text or file"""
        response = client.post("/estimate", json={}, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No text or file provided" in response.json()["detail"]

    def test_estimate_cost_no_models(self, client, auth_headers, sample_document_text):
        """Test cost estimation when no models are available"""
        with patch('services.crud.model.get_active_models') as mock_get_models:
            mock_get_models.return_value = []
            
            response = client.post("/estimate",
                                 json={"document_text": sample_document_text},
                                 headers=auth_headers)
            
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No models available" in response.json()["detail"]


class TestPredictionIntegration:
    """Test prediction integration scenarios"""

    def test_full_prediction_workflow(self, client, auth_headers, sample_document_text):
        """Test complete prediction workflow"""
        # 1. Top up balance
        topup_response = client.post("/wallet/topup", json={"amount": 100.0}, headers=auth_headers)
        assert topup_response.status_code == status.HTTP_200_OK
        
        # 2. Get cost estimation
        with patch('services.crud.model.get_active_models') as mock_get_models, \
             patch('models.document.Document.count_tokens') as mock_count_tokens:
            
            mock_model = MagicMock()
            mock_model.name = "test_model"
            mock_model.price_per_token = 0.1
            
            mock_get_models.return_value = [mock_model]
            mock_count_tokens.return_value = 100
            
            estimate_response = client.post("/estimate", 
                                          json={"document_text": sample_document_text},
                                          headers=auth_headers)
        
        assert estimate_response.status_code == status.HTTP_200_OK
        
        # 3. Submit prediction
        with patch('services.prediction_service.process_prediction_request') as mock_predict:
            mock_predict.return_value = {
                "message": "Prediction queued successfully",
                "job_id": 1,
                "document_id": 1,
                "status": "PENDING",
                "cost": 10.0,
                "tokens_processed": 100
            }
            
            prediction_data = {
                "document_text": sample_document_text,
                "filename": "test_contract.txt"
            }
            
            predict_response = client.post("/predict", json=prediction_data, headers=auth_headers)
        
        assert predict_response.status_code == status.HTTP_200_OK
        
        # 4. Check job status
        with patch('services.crud.mljob.get_job_by_id') as mock_get_job, \
             patch('services.crud.document.get_document_by_id') as mock_get_doc, \
             patch('services.crud.mljob.get_job_risk_clauses') as mock_get_clauses:
            
            mock_job = MagicMock()
            mock_job.id = 1
            mock_job.document_id = 1
            mock_job.status = "COMPLETED"
            
            mock_document = MagicMock()
            mock_document.user_id = 1
            
            mock_get_job.return_value = mock_job
            mock_get_doc.return_value = mock_document
            mock_get_clauses.return_value = []
            
            job_response = client.get("/jobs/1", headers=auth_headers)
        
        assert job_response.status_code == status.HTTP_200_OK
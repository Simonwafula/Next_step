"""
Payment service for handling premium subscriptions and payments
Integrates with M-Pesa and other Kenyan payment methods
"""

import logging
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db.models import User, Subscription, Payment, PaymentMethod
import requests
import asyncio

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Service for handling payments and subscriptions for premium features
    """
    
    def __init__(self):
        # M-Pesa API configuration (you'll need to set these from environment variables)
        self.mpesa_consumer_key = "your_mpesa_consumer_key"
        self.mpesa_consumer_secret = "your_mpesa_consumer_secret"
        self.mpesa_shortcode = "174379"  # Example shortcode
        self.mpesa_passkey = "your_mpesa_passkey"
        self.mpesa_callback_url = "https://yourdomain.com/api/payments/mpesa/callback"
        
        # Stripe configuration for international payments
        self.stripe_secret_key = "your_stripe_secret_key"
        self.stripe_publishable_key = "your_stripe_publishable_key"
        
        # Payment plans
        self.payment_plans = {
            "professional": {
                "name": "Professional",
                "price": 2500,  # KSh
                "currency": "KES",
                "duration_days": 30,
                "features": [
                    "ai_cv_optimization",
                    "personalized_cover_letters", 
                    "advanced_career_coaching",
                    "priority_job_alerts",
                    "salary_negotiation_tips"
                ]
            },
            "enterprise": {
                "name": "Enterprise", 
                "price": 5000,  # KSh
                "currency": "KES",
                "duration_days": 30,
                "features": [
                    "one_on_one_coaching",
                    "interview_preparation",
                    "linkedin_optimization",
                    "recruiter_connections",
                    "custom_job_alerts"
                ]
            }
        }
        
    async def initiate_mpesa_payment(self, user_id: int, plan_id: str, phone_number: str) -> Dict:
        """
        Initiate M-Pesa STK Push payment
        
        Args:
            user_id: User ID
            plan_id: Payment plan ID
            phone_number: User's phone number
            
        Returns:
            Payment initiation response
        """
        try:
            plan = self.payment_plans.get(plan_id)
            if not plan:
                return {"success": False, "error": "Invalid payment plan"}
                
            # Get M-Pesa access token
            access_token = await self._get_mpesa_access_token()
            if not access_token:
                return {"success": False, "error": "Failed to get M-Pesa access token"}
                
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}".encode()
            ).decode('utf-8')
            
            # Prepare STK Push request
            stk_push_data = {
                "BusinessShortCode": self.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": plan["price"],
                "PartyA": phone_number,
                "PartyB": self.mpesa_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.mpesa_callback_url,
                "AccountReference": f"CareerSearch-{plan_id}",
                "TransactionDesc": f"Payment for {plan['name']} subscription"
            }
            
            # Make STK Push request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=stk_push_data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Save payment record
                payment_id = await self._save_payment_record(
                    user_id=user_id,
                    plan_id=plan_id,
                    amount=plan["price"],
                    currency=plan["currency"],
                    payment_method="mpesa",
                    external_id=response_data.get("CheckoutRequestID"),
                    status="pending"
                )
                
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "checkout_request_id": response_data.get("CheckoutRequestID"),
                    "merchant_request_id": response_data.get("MerchantRequestID"),
                    "message": "Payment initiated. Please complete on your phone."
                }
            else:
                logger.error(f"M-Pesa STK Push failed: {response.text}")
                return {"success": False, "error": "Failed to initiate payment"}
                
        except Exception as e:
            logger.error(f"Error initiating M-Pesa payment: {e}")
            return {"success": False, "error": str(e)}
            
    async def handle_mpesa_callback(self, callback_data: Dict) -> Dict:
        """
        Handle M-Pesa payment callback
        
        Args:
            callback_data: Callback data from M-Pesa
            
        Returns:
            Processing result
        """
        try:
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            
            if result_code == 0:  # Success
                # Extract payment details
                callback_metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                payment_details = {}
                
                for item in callback_metadata:
                    name = item.get("Name")
                    value = item.get("Value")
                    if name == "Amount":
                        payment_details["amount"] = value
                    elif name == "MpesaReceiptNumber":
                        payment_details["receipt_number"] = value
                    elif name == "PhoneNumber":
                        payment_details["phone_number"] = value
                        
                # Update payment record
                await self._update_payment_status(
                    external_id=checkout_request_id,
                    status="completed",
                    payment_details=payment_details
                )
                
                # Activate subscription
                await self._activate_subscription(checkout_request_id)
                
                return {"success": True, "message": "Payment processed successfully"}
                
            else:
                # Payment failed
                await self._update_payment_status(
                    external_id=checkout_request_id,
                    status="failed",
                    payment_details={"result_code": result_code}
                )
                
                return {"success": False, "message": "Payment failed"}
                
        except Exception as e:
            logger.error(f"Error handling M-Pesa callback: {e}")
            return {"success": False, "error": str(e)}
            
    async def create_stripe_payment_intent(self, user_id: int, plan_id: str) -> Dict:
        """
        Create Stripe payment intent for international payments
        
        Args:
            user_id: User ID
            plan_id: Payment plan ID
            
        Returns:
            Payment intent details
        """
        try:
            import stripe
            stripe.api_key = self.stripe_secret_key
            
            plan = self.payment_plans.get(plan_id)
            if not plan:
                return {"success": False, "error": "Invalid payment plan"}
                
            # Convert KES to USD (approximate rate)
            amount_usd = int(plan["price"] / 130 * 100)  # Convert to cents
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_usd,
                currency='usd',
                metadata={
                    'user_id': user_id,
                    'plan_id': plan_id,
                    'original_amount': plan["price"],
                    'original_currency': plan["currency"]
                }
            )
            
            # Save payment record
            payment_id = await self._save_payment_record(
                user_id=user_id,
                plan_id=plan_id,
                amount=plan["price"],
                currency=plan["currency"],
                payment_method="stripe",
                external_id=intent.id,
                status="pending"
            )
            
            return {
                "success": True,
                "payment_id": payment_id,
                "client_secret": intent.client_secret,
                "publishable_key": self.stripe_publishable_key
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe payment intent: {e}")
            return {"success": False, "error": str(e)}
            
    async def handle_stripe_webhook(self, payload: str, signature: str) -> Dict:
        """
        Handle Stripe webhook events
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            
        Returns:
            Processing result
        """
        try:
            import stripe
            stripe.api_key = self.stripe_secret_key
            
            # Verify webhook signature
            endpoint_secret = "your_stripe_webhook_secret"
            event = stripe.Webhook.construct_event(
                payload, signature, endpoint_secret
            )
            
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                
                # Update payment record
                await self._update_payment_status(
                    external_id=payment_intent['id'],
                    status="completed",
                    payment_details={
                        "amount_received": payment_intent['amount_received'],
                        "currency": payment_intent['currency']
                    }
                )
                
                # Activate subscription
                await self._activate_subscription(payment_intent['id'])
                
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                
                await self._update_payment_status(
                    external_id=payment_intent['id'],
                    status="failed",
                    payment_details={
                        "failure_reason": payment_intent.get('last_payment_error', {}).get('message')
                    }
                )
                
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error handling Stripe webhook: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_mpesa_access_token(self) -> Optional[str]:
        """Get M-Pesa API access token"""
        try:
            auth_string = f"{self.mpesa_consumer_key}:{self.mpesa_consumer_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Failed to get M-Pesa access token: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting M-Pesa access token: {e}")
            return None
            
    async def _save_payment_record(self, user_id: int, plan_id: str, amount: float, 
                                 currency: str, payment_method: str, external_id: str, 
                                 status: str) -> int:
        """Save payment record to database"""
        db = SessionLocal()
        try:
            payment = Payment(
                user_id=user_id,
                plan_id=plan_id,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                external_id=external_id,
                status=status,
                created_at=datetime.utcnow()
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)
            return payment.id
            
        except Exception as e:
            logger.error(f"Error saving payment record: {e}")
            db.rollback()
            return None
        finally:
            db.close()
            
    async def _update_payment_status(self, external_id: str, status: str, 
                                   payment_details: Dict = None):
        """Update payment status in database"""
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(
                Payment.external_id == external_id
            ).first()
            
            if payment:
                payment.status = status
                payment.payment_details = json.dumps(payment_details) if payment_details else None
                payment.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Updated payment {payment.id} status to {status}")
            else:
                logger.warning(f"Payment with external_id {external_id} not found")
                
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            db.rollback()
        finally:
            db.close()
            
    async def _activate_subscription(self, external_id: str):
        """Activate user subscription after successful payment"""
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(
                Payment.external_id == external_id,
                Payment.status == "completed"
            ).first()
            
            if not payment:
                logger.error(f"Completed payment with external_id {external_id} not found")
                return
                
            plan = self.payment_plans.get(payment.plan_id)
            if not plan:
                logger.error(f"Plan {payment.plan_id} not found")
                return
                
            # Check if user already has an active subscription
            existing_subscription = db.query(Subscription).filter(
                Subscription.user_id == payment.user_id,
                Subscription.status == "active"
            ).first()
            
            if existing_subscription:
                # Extend existing subscription
                existing_subscription.end_date = existing_subscription.end_date + timedelta(
                    days=plan["duration_days"]
                )
                existing_subscription.updated_at = datetime.utcnow()
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=payment.user_id,
                    plan_id=payment.plan_id,
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=plan["duration_days"]),
                    status="active",
                    features=json.dumps(plan["features"]),
                    created_at=datetime.utcnow()
                )
                db.add(subscription)
                
            db.commit()
            logger.info(f"Activated subscription for user {payment.user_id}")
            
        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            db.rollback()
        finally:
            db.close()
            
    async def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Get user's current subscription details"""
        db = SessionLocal()
        try:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == "active",
                Subscription.end_date > datetime.utcnow()
            ).first()
            
            if subscription:
                return {
                    "id": subscription.id,
                    "plan_id": subscription.plan_id,
                    "plan_name": self.payment_plans.get(subscription.plan_id, {}).get("name"),
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                    "status": subscription.status,
                    "features": json.loads(subscription.features) if subscription.features else [],
                    "days_remaining": (subscription.end_date - datetime.utcnow()).days
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None
        finally:
            db.close()
            
    async def check_feature_access(self, user_id: int, feature: str) -> bool:
        """Check if user has access to a specific premium feature"""
        subscription = await self.get_user_subscription(user_id)
        
        if not subscription:
            return False
            
        return feature in subscription.get("features", [])
        
    async def get_payment_history(self, user_id: int) -> List[Dict]:
        """Get user's payment history"""
        db = SessionLocal()
        try:
            payments = db.query(Payment).filter(
                Payment.user_id == user_id
            ).order_by(Payment.created_at.desc()).all()
            
            return [
                {
                    "id": payment.id,
                    "plan_id": payment.plan_id,
                    "plan_name": self.payment_plans.get(payment.plan_id, {}).get("name"),
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "payment_method": payment.payment_method,
                    "status": payment.status,
                    "created_at": payment.created_at,
                    "updated_at": payment.updated_at
                }
                for payment in payments
            ]
            
        except Exception as e:
            logger.error(f"Error getting payment history: {e}")
            return []
        finally:
            db.close()
            
    def get_available_plans(self) -> Dict:
        """Get all available payment plans"""
        return self.payment_plans

# Global service instance
payment_service = PaymentService()

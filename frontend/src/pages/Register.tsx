import { useState, useEffect } from "react";
import type { FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Container,
  Row,
  Col,
  Form,
  Button,
  Alert,
  Card,
  Spinner,
} from "react-bootstrap";
import { useAuth } from "../context/useAuth";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const { register, error, success, loading, resetMessages } = useAuth();
  const navigate = useNavigate();

  // Reset messages when component mounts
  useEffect(() => {
    resetMessages();
  }, [resetMessages]);

  // Navigate after successful registration
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => navigate("/"), 1500);
      return () => clearTimeout(timer);
    }
  }, [success, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordError("");

    if (password !== confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }

    try {
      await register(name, email, password);
    } catch {
      // Error is handled in the auth context
    }
  };

  return (
    <div
      style={{ minHeight: "100vh", width: "100vw" }}
      className="d-flex align-items-center justify-content-center bg-light"
    >
      <Container fluid="md" className="mx-3">
        <Row className="justify-content-center">
          <Col xs={12} sm={10} md={8} lg={6} xl={4}>
            <Card className="shadow">
              <Card.Body className="p-4">
                <h2 className="text-center mb-4">Create Account</h2>

                <Form onSubmit={handleSubmit}>
                  {(error || passwordError) && (
                    <Alert variant="danger" className="mb-4">
                      {error || passwordError}
                    </Alert>
                  )}

                  {success && (
                    <Alert variant="success" className="mb-4">
                      {success}
                    </Alert>
                  )}

                  <Form.Group className="mb-3">
                    <Form.Label>Full Name</Form.Label>
                    <Form.Control
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      placeholder="Enter your full name"
                      disabled={loading}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>Email address</Form.Label>
                    <Form.Control
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="Enter email"
                      disabled={loading}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>Password</Form.Label>
                    <Form.Control
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="Password"
                      disabled={loading}
                    />
                  </Form.Group>

                  <Form.Group className="mb-4">
                    <Form.Label>Confirm Password</Form.Label>
                    <Form.Control
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      placeholder="Confirm password"
                      disabled={loading}
                    />
                  </Form.Group>

                  <Button
                    variant="primary"
                    type="submit"
                    disabled={loading}
                    className="w-100 mb-3"
                  >
                    {loading ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        Creating account...
                      </>
                    ) : (
                      "Sign Up"
                    )}
                  </Button>

                  <div className="text-center">
                    <Link
                      to="/login"
                      className="text-decoration-none"
                      tabIndex={loading ? -1 : 0}
                    >
                      Already have an account? Sign In
                    </Link>
                  </div>
                </Form>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
}

import { useAuth } from "../context/useAuth";
import { useNavigate } from "react-router-dom";
import { Container, Navbar, Button, Card } from "react-bootstrap";

export default function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-vh-100 bg-light">
      <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
        <Container>
          <Navbar.Brand>Dashboard</Navbar.Brand>
          <Navbar.Toggle />
          <Navbar.Collapse className="justify-content-end">
            <Button variant="outline-light" onClick={handleLogout}>
              Logout
            </Button>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container className="py-4">
        <Card className="shadow-sm">
          <Card.Body>
            <Card.Title className="h4 mb-3">
              Welcome back, {user?.name}!
            </Card.Title>
            <Card.Text className="text-muted">
              You are logged in with {user?.email}
            </Card.Text>
          </Card.Body>
        </Card>
      </Container>
    </div>
  );
}

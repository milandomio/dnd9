import { useEffect, useState } from "react";
import { Card, Col, Row, Spin, Statistic } from "antd";
import { useNavigate } from "react-router-dom";
import type { IndexEntry } from "../types/data";

export default function HomePage() {
  const [data, setData] = useState<IndexEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("./data/index.json")
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <Row gutter={[16, 16]}>
      {data.map((entry) => (
        <Col key={entry.page} xs={12} sm={8} md={6}>
          <Card
            hoverable
            onClick={() => navigate(`/${entry.page}`)}
            style={{ textAlign: "center" }}
          >
            <Statistic title={entry.label} value={entry.count} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}

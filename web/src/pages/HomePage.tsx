import { Card, Col, Row, Typography, Spin } from "antd";
import { useEffect, useState } from "react";
import type { GameItem } from "../types/data";

const DATA_URL = "./data.json";

export default function HomePage() {
  const [data, setData] = useState<GameItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(DATA_URL)
      .then((res) => res.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div>
      <Typography.Title level={4}>
        共 {data.length} 条记录
      </Typography.Title>
      <Row gutter={[16, 16]}>
        {data.map((item) => (
          <Col key={item.id} xs={24} sm={12} md={8} lg={6}>
            <Card title={item.name} size="small" hoverable>
              <Typography.Text type="secondary">{item.category}</Typography.Text>
              {item.description && (
                <Typography.Paragraph style={{ marginTop: 8 }}>
                  {item.description}
                </Typography.Paragraph>
              )}
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}

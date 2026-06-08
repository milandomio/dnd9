import { useEffect, useState } from "react";
import { Card, Col, Row, Spin, Typography, Tag } from "antd";
import { useParams, useNavigate } from "react-router-dom";
import type { ItemEntity, MonsterEntity, PropsEntity } from "../types/data";

type Entity = ItemEntity | MonsterEntity | PropsEntity;

const LABEL_MAP: Record<string, string> = {
  items: "物品表",
  monsters: "怪物表",
  props: "实体表",
};

export default function ListPage() {
  const { page } = useParams<{ page: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!page || !["items", "monsters", "props"].includes(page)) return;
    fetch(`./data/${page}.json`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page]);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <Typography.Title level={4}>{LABEL_MAP[page!] ?? page}（{data.length}）</Typography.Title>
      <Row gutter={[16, 16]}>
        {data.map((entity) => (
          <Col key={entity.name} xs={24} sm={12} md={8}>
            <Card
              title={entity.translation || entity.name}
              size="small"
              hoverable
              onClick={() => navigate(`/${page}/${entity.name}`)}
            >
              <Typography.Text code>{entity.name}</Typography.Text>
              {"monsters" in entity && entity.monsters && entity.monsters.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Tag color="blue">{entity.monsters.length} 掉落</Tag>
                </div>
              )}
              <div style={{ marginTop: 4 }}>
                <Tag>{entity.coords.length} 坐标</Tag>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}

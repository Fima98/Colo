import Card from "@/components/Card";
import DraggableCard from "@/components/DraggableCard";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="w-screen">
      <Button>Button</Button>;<h1 className="bg-primary">ghdfkjgfhd</h1>
      <DraggableCard>
        <Card value="1" color="orange" />
      </DraggableCard>
      <DraggableCard>
        <Card value="wild" />
      </DraggableCard>
    </div>
  );
}

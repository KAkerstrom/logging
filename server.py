from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import uvicorn

host = "0.0.0.0"
port = 8100

DATABASE_URL = "sqlite:///./data/property_logs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Property(Base):
    __tablename__ = "properties"
    PropertyId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Number = Column(String, index=True)
    Notes = Column(String)


class Log(Base):
    __tablename__ = "logs"
    PropertyId = Column(Integer, ForeignKey("properties.PropertyId"), nullable=False)
    EventId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Timestamp = Column(DateTime, default=func.now())
    Description = Column(String)


Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/properties/")
def create_property(number: str, notes: str, db: Session = Depends(get_db)):
    """Create a property in the database."""
    property_ = Property(Number=number, Notes=notes)
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return property_


@app.get("/properties/")
def get_all_properties(db: Session = Depends(get_db)):
    """Get a list of all properties in the database."""
    properties = db.query(Property.PropertyId, Property.Number).all()
    return [Property(PropertyId=p.PropertyId, Number=p.Number) for p in properties]


@app.get("/properties/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get a property from the database, including notes."""
    property_ = db.query(Property).filter(Property.PropertyId == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")
    return property_


@app.put("/properties/{property_id}")
def update_property(
    property_id: int, number: str, notes: str, db: Session = Depends(get_db)
):
    """Update a property's base information in the database."""
    property_ = db.query(Property).filter(Property.PropertyId == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")
    property_.Number = number
    property_.Notes = notes
    db.commit()
    return property_


# Note that we should typically not permanently delete data.
# Instead, we should simply set a flag on the property to hide it from results.
# For simplicity's sake, for now I'm going to delete it, though.
@app.delete("/properties/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)):
    """Permanently delete a property in the database, along with all associated events."""
    # Retrieve the property
    property_ = db.query(Property).filter(Property.PropertyId == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")

    # Delete all logs associated with the property
    logs = db.query(Log).filter(Log.PropertyId == property_id).all()
    for log in logs:
        db.delete(log)

    # Delete the property itself
    db.delete(property_)
    db.commit()
    return {"message": "Property and associated logs deleted."}


@app.get("/properties/{property_id}/events")
def get_events_for_property(property_id: int, db: Session = Depends(get_db)):
    """Get all the events associated with a property."""
    logs = db.query(Log).filter(Log.PropertyId == property_id).all()
    if not logs:
        raise HTTPException(
            status_code=404, detail="No events found for this property."
        )
    return [
        Log(
            PropertyId=log.PropertyId,
            EventId=log.EventId,
            Timestamp=log.Timestamp,
            Description=log.Description,
        )
        for log in logs
    ]


@app.post("/properties/{property_id}/events/")
def create_event(property_id: int, description: str, db: Session = Depends(get_db)):
    """Log a new event for the given property."""
    log = Log(PropertyId=property_id, Description=description)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@app.get("/properties/{property_id}/events/{event_id}")
def get_log(property_id: int, event_id: int, db: Session = Depends(get_db)):
    """Get an event for the given property."""
    log = (
        db.query(Log)
        .filter(Log.PropertyId == property_id and Log.EventId == event_id)
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found.")
    return log


# Note that we should typically not permanently delete data.
# Instead, we should simply set a flag on the property to hide it from results.
# For simplicity's sake, for now I'm going to delete it, though.
@app.delete("/properties/{property_id}/events/{event_id}")
def delete_event(property_id: int, event_id: int, db: Session = Depends(get_db)):
    """Permanently delete an event from the database."""
    log = (
        db.query(Property)
        .filter(Log.PropertyId == property_id and Log.EventId == event_id)
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(log)
    db.commit()
    return {"message": "Event deleted"}


@app.get("/properties/{property_id}/events")
def get_property_logs(property_id: int, db: Session = Depends(get_db)):
    logs = db.query(Log).filter(Log.PropertyId == property_id).all()
    return logs


if __name__ == "__main__":
    uvicorn.run("server:app", host=host, port=port, reload=True)

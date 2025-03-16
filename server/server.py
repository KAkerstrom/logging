### Imports ###
import os
from datetime import datetime, time
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import uvicorn

### Define constants ###
DATABASE_URL = "sqlite:////app/data/property_logs.db"

### Set up database ###
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


### Define SQLAlchemy models ###
class Property(Base):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    number = Column(String(100), index=True, nullable=False)
    notes = Column(Text, nullable=True)


class Log(Base):
    __tablename__ = "logs"
    propertyId = Column(Integer, ForeignKey("properties.id"), nullable=False)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now())
    description = Column(Text)


### Set up FastAPI ###
tags_metadata = [
    {
        "name": "properties",
        "description": "Operations relating to Properties.",
    },
    {
        "name": "events",
        "description": "Operations relating to Events (which are tied to Properties).",
    },
]

app = FastAPI(
    title="Property Event Logging",
    description="A simple database API server for logging events relating to properties.",
    version="1",
    openapi_tags=tags_metadata,
)


### Helper methods ###
def init_db(base, engine):
    base.metadata.create_all(bind=engine)
    print("Initialized database.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validateDateTime(
    dateTimeString: str, defaultTime: time = time.min
) -> datetime | None:
    try:
        parsedDateTime = datetime.fromisoformat(dateTimeString)
        if parsedDateTime:
            parsedTime = parsedDateTime.time()
            return (
                datetime.combine(parsedDateTime, defaultTime)
                if parsedTime == time.min
                else parsedDateTime
            )
        return None
    except ValueError:
        return None


# Create the database if it doesn't exist
init_db(Base, engine)


### Property endpoints ###
@app.post("/properties/", tags=["properties"])
def create_property(number: str, notes: str, db: Session = Depends(get_db)):
    """Create a property in the database."""
    property_ = Property(number=number, notes=notes)
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return property_


@app.get("/properties/", tags=["properties"])
def get_all_properties(db: Session = Depends(get_db)):
    """Get a list of all properties in the database."""
    properties = db.query(Property.id, Property.number, Property.notes).all()
    return [
        Property(
            id=p.id,
            number=p.number,
            notes=p.notes,
        )
        for p in properties
    ]


@app.get("/properties/{property_id}", tags=["properties"])
def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get a property from the database, including notes."""
    property_ = db.query(Property).filter(Property.id == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")
    return property_


@app.put("/properties/{property_id}", tags=["properties"])
def update_property(
    property_id: int, number: str, notes: str, db: Session = Depends(get_db)
):
    """Update a property's base information in the database."""
    property_ = db.query(Property).filter(Property.id == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")
    property_.number = number
    property_.notes = notes
    db.commit()
    return property_


# Note that we should typically not permanently delete data.
# Instead, we should simply set a flag on the property to hide it from results.
# For simplicity's sake, for now I'm going to delete it, though.
@app.delete("/properties/{property_id}", tags=["properties"])
def delete_property(property_id: int, db: Session = Depends(get_db)):
    """Permanently delete a property in the database, along with all associated events."""
    # Retrieve the property
    property_ = db.query(Property).filter(Property.id == property_id).first()
    if property_ is None:
        raise HTTPException(status_code=404, detail="Property not found.")

    # Delete all logs associated with the property
    logs = db.query(Log).filter(Log.propertyId == property_id).all()
    for log in logs:
        db.delete(log)

    # Delete the property itself
    db.delete(property_)
    db.commit()
    return {"message": "Property and associated logs deleted."}


### Event endpoints ###
@app.get("/properties/{property_id}/events", tags=["events"])
def get_property_events(
    property_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    """Get all the events associated with a property. Optionally filter by date/time range."""
    query = db.query(Log).filter(Log.propertyId == property_id)

    if start_date:
        parsed_start = validateDateTime(start_date, time.min)
        if parsed_start:
            query = query.filter(Log.timestamp >= parsed_start)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unable to parse start_date. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            )

    if end_date:
        parsed_end = validateDateTime(end_date, time.max)
        if parsed_end:
            query = query.filter(Log.timestamp >= parsed_end)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unable to parse end_date. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            )

    logs = query.all()
    if not logs:
        if start_date or end_date:
            error_detail = "No events found for this property in the given range."
        else:
            error_detail = "No events found for this property."
        raise HTTPException(status_code=404, detail=error_detail)

    return [
        Log(
            id=log.id,
            propertyId=log.propertyId,
            timestamp=log.timestamp,
            description=log.description,
        )
        for log in logs
    ]


@app.post("/properties/{property_id}/events/", tags=["events"])
def create_event(
    property_id: int,
    description: str,
    timestamp: str | None = None,
    db: Session = Depends(get_db),
):
    """Log a new event for the given property."""
    if timestamp:
        parsed_timestamp = validateDateTime(timestamp, time.min)
        if not parsed_timestamp:
            raise HTTPException(
                status_code=400,
                detail="Unable to parse timestamp. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
            )
    else:
        parsed_timestamp = datetime.now()

    log = Log(
        propertyId=property_id, timestamp=parsed_timestamp, description=description
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@app.get("/properties/{property_id}/events/{event_id}", tags=["events"])
def get_event(property_id: int, event_id: int, db: Session = Depends(get_db)):
    """Get an event for the given property."""
    log = (
        db.query(Log)
        .filter(Log.propertyId == property_id and Log.id == event_id)
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found.")
    return log


# Note that we should typically not permanently delete data.
# Instead, we should simply set a flag on the property to hide it from results.
# For simplicity's sake, for now I'm going to delete it, though.
@app.delete("/properties/{property_id}/events/{event_id}", tags=["events"])
def delete_event(property_id: int, event_id: int, db: Session = Depends(get_db)):
    """Permanently delete an event from the database."""
    log = (
        db.query(Property)
        .filter(Log.propertyId == property_id and Log.id == event_id)
        .first()
    )
    if log is None:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(log)
    db.commit()
    return {"message": "Event deleted"}


if __name__ == "__main__":

    host = int(os.getenv("HOST", "0.0.0.0"))
    port = int(os.getenv("PORT", 8100))
    uvicorn.run("server:app", host=host, port=port, reload=True)

# AI Voice Calling Platform

A multilingual AI voice-agent platform that enables clinics to automate patient calls, appointment scheduling, and WhatsApp confirmations through conversational AI.

## Overview

This project provides an AI-powered voice calling system designed for healthcare workflows. The platform handles patient conversations in real time, understands appointment-related requests, retrieves clinic-specific information, schedules appointments, and sends confirmation messages.

The backend is built as a multi-tenant FastAPI application, allowing different clinics to configure their own doctors, services, availability, and appointment slots.

## Key Features

- 🎙️ **Real-time AI Voice Agents**
  - Conversational voice interactions using Gemini Live
  - Supports multilingual patient conversations
  - Handles appointment-related queries naturally

- 🏥 **Multi-Tenant Architecture**
  - Clinic-specific doctors, services, and appointment slots
  - Dynamic context injection into the AI agent
  - Isolated configuration for different healthcare providers

- 📅 **Automated Appointment Booking**
  - Extracts structured booking information from conversations
  - Integrates with Google Calendar
  - Checks doctor availability before scheduling

- 💬 **WhatsApp Confirmations**
  - Sends appointment confirmations after successful bookings
  - Integrates voice interactions with downstream communication

- 🔎 **RAG-Based Information Retrieval**
  - Retrieves clinic-specific information during conversations
  - Uses vector search for contextual responses

- ⚡ **Asynchronous Processing**
  - Async transcript collection
  - Structured JSON extraction from conversations
  - Efficient handling of concurrent calls

- 🗄️ **Persistent Data Layer**
  - Stores appointment and conversation information
  - Supports structured SQL-based data management

## System Architecture

```text
                    ┌─────────────────────┐
                    │      Patient        │
                    │   Phone Call        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Twilio        │
                    │  Voice Infrastructure│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    │   Multi-Tenant API  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          ┌────────────┐ ┌────────────┐ ┌────────────┐
          │ Gemini Live│ │  RAG /     │ │ SQL DB     │
          │ Voice Agent│ │ ChromaDB   │ │            │
          └────────────┘ └────────────┘ └────────────┘
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Booking Extraction  │
                    │ Doctor / Slot / Date│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Google Calendar    │
                    │ Appointment Booking │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ WhatsApp Confirmation│
                    └─────────────────────┘

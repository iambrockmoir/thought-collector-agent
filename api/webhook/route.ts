import { NextResponse } from 'next/server';
import twilio from 'twilio';
import axios from 'axios';

// Twilio credentials from environment variables
const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const client = twilio(accountSid, authToken);

export async function POST(req: Request) {
    try {
        const data = await req.formData();
        const numMedia = parseInt(data.get('NumMedia') as string || '0');
        const messageSid = data.get('MessageSid');
        
        console.log('Received webhook:', {
            numMedia,
            messageSid,
            from: data.get('From'),
            body: data.get('Body')
        });

        if (numMedia > 0) {
            // Get the media from the message
            const mediaList = await client.messages(messageSid as string).media.list();
            const media = mediaList[0];
            
            if (!media) {
                console.error('No media found in message');
                return NextResponse.json({ error: 'No media found' }, { status: 400 });
            }

            // Construct the media URL
            const mediaUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages/${messageSid}/Media/${media.sid}`;
            
            // Download the media content
            const mediaResponse = await axios.get(mediaUrl, {
                auth: {
                    username: accountSid as string,
                    password: authToken as string
                },
                headers: {
                    'Accept': 'audio/amr'
                },
                responseType: 'arraybuffer'
            });

            // Create form data for the converter
            const formData = new FormData();
            const audioBlob = new Blob([mediaResponse.data], { type: 'audio/amr' });
            formData.append('audio', audioBlob, 'audio.amr');

            // Send to converter service
            console.log('Sending to converter service...');
            const converterResponse = await axios.post(
                'https://audio-converter-service-production.up.railway.app/convert',
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    },
                    responseType: 'arraybuffer'
                }
            );

            // Process the converted audio
            if (converterResponse.status === 200) {
                console.log('Conversion successful');
                // Here you can store or process the MP3 file
                // For example, save it to a storage service or process it further
                
                return NextResponse.json({ 
                    success: true,
                    message: 'Audio converted successfully'
                });
            } else {
                console.error('Conversion failed:', converterResponse.status);
                return NextResponse.json({ 
                    error: 'Conversion failed' 
                }, { status: 500 });
            }
        }
    } catch (error) {
        console.error('Error processing webhook:', error);
        return NextResponse.json({ 
            error: 'An error occurred while processing the webhook' 
        }, { status: 500 });
    }
} 